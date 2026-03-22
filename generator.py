import os
import re
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import pipeline
import torch
import json
import math
from huggingface_hub import InferenceClient
from datetime import datetime

from tech_metrics import (
    log_generation_attempt,
    extract_usage,
    estimate_tokens,
)

current_dir = os.path.dirname(os.path.abspath(__file__)) 
index_path = os.path.join(current_dir, "faiss_index")


class ResponseGenerator:

    def __init__(self, hf_token, model="Qwen/Qwen2.5-7B-Instruct", system_prompt=None):
        self.client = InferenceClient(model=model, token=hf_token)
        self.model = model
        self.provider = "huggingface_inference"

        embeddings = HuggingFaceEmbeddings(
            model_name="deepvk/USER-base",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        self.vector_store = FAISS.load_local(
            index_path, embeddings, allow_dangerous_deserialization=True
        )

        if system_prompt is None:
            self.system_prompt = """Ты — эксперт-юрист, навигатор по законодательству РФ.
                Отвечай, используя ТОЛЬКО информацию из предоставленного контекста.
                Не давай индивидуальные юридические рекомендации, ничего не советуй, используй безличные конструкции.
                Ни в коем случае не давай советы о том, как лучше совершить противозаконное действие или обойти закон. 
                Если в контексте нет ответа — откажись отвечать.
                ОТВЕЧАЙ СТРОГО НА РУССКОМ ЯЗЫКЕ. ИСПОЛЬЗОВАНИЕ КИТАЙСКИХ ИЕРОГЛИФОВ ЗАПРЕЩЕНО.
                В ходе ответа обязательно укажи ссылки на использованные статьи.
                Используй официально-деловой стиль, без эмодзи.
                Ответ должен быть максимально структурированным, пиши по пунктам, а не слитным текстом.
                Не пиши все в одну строку, используй переносы на новую строку где это уместно и логично.
                Если тебе задают вопрос ПО ТЕМЕ, то в самом конце ответа на отдельной строке указывай: "Дисклеймер: бот является навигатором по законодательству РФ и не заменяет квалифицированную юридическую помощь." 
                Указывай дисклеймер ТОЛЬКО ЕСЛИ вопрос ПО ТЕМЕ и находится в рамках навигатора по законам.
                Если тебе задают вопрос не по теме, то НЕ ОТВЕЧАЙ на него и укажи в конце ответа, что вопрос выходит за рамки компетенций навигатора по законам.
                """
        else:
            self.system_prompt = system_prompt

    def get_context(self, question, k):
        results = self.vector_store.similarity_search(question, k=k)
        context = '\n'.join([x.page_content for x in results])
        return context, len(results)
    
    def get_response(self, question, context, max_tokens):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Контекст документов:
{context}

Вопрос пользователя: {question}
"""}
        ]
          
        response_raw = self.client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.5,
            logprobs=True,
            top_logprobs=1
        )
        return response_raw, messages

    def is_russian_only(self, response):
        pattern = re.compile(r'^[а-яё0-9\s\d.,!?;:()"\-«»№/\n]+$', re.IGNORECASE)
        return bool(pattern.match(response))
    
    def get_confidence(self, logprobs):
        if not logprobs:
            return 0.0
        logprobs = sum(logprobs) / len(logprobs)
        return math.exp(logprobs)

    def generate(self, question, request_id=None, max_tokens=3000, conf_thresh=0.75):
        started_at = time.perf_counter()

        success = False
        fallback_response = 'Я не обладаю достаточной информацией для ответа на данный вопрос. Пожалуйста, проконсультируйтесь с квалицицированным специалистом.'
        final_response = fallback_response

        metrics = {
            "request_id": request_id,
            "pipeline_status": "fallback",
            "error_stage": None,
            "error_type": None,
            "error_message": None,

            "llm_provider": self.provider,
            "llm_model": self.model,

            "retrieval_k": 10,
            "retrieved_docs_count": 0,

            "generation_attempts": 0,
            "successful_attempt": None,
            "russian_only_flag": 0,
            "confidence_score": None,
            "confidence_threshold": conf_thresh,

            "input_chars": len(question) if question else 0,
            "output_chars": 0,

            "retrieval_latency_sec": None,
            "generation_latency_sec": None,
            "total_latency_sec": None,

            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,

            "est_prompt_tokens": None,
            "est_completion_tokens": None,
            "est_total_tokens": None,
        }

        # Слишком длинные тексты - подозрение на взлом, сразу заглушка
        if len(question) > 1000:
            metrics["pipeline_status"] = "fallback"
            metrics["error_stage"] = "validation"
            metrics["error_type"] = "question_too_long"
            metrics["error_message"] = f"Question length is {len(question)} chars"
            metrics["total_latency_sec"] = time.perf_counter() - started_at
            return final_response, metrics

        try:
            retrieval_started = time.perf_counter()
            context, retrieved_docs_count = self.get_context(question=question, k=10)
            metrics["retrieval_latency_sec"] = time.perf_counter() - retrieval_started
            metrics["retrieved_docs_count"] = retrieved_docs_count
        except Exception as e:
            metrics["pipeline_status"] = "error"
            metrics["error_stage"] = "retrieval"
            metrics["error_type"] = type(e).__name__
            metrics["error_message"] = str(e)
            metrics["total_latency_sec"] = time.perf_counter() - started_at
            return final_response, metrics

        final_response = fallback_response
        total_generation_time = 0.0

        for trial in range(3):
            attempt_no = trial + 1
            metrics["generation_attempts"] = attempt_no

            attempt_started = time.perf_counter()
            try:
                response_raw, messages = self.get_response(
                    question=question,
                    context=context,
                    max_tokens=max_tokens
                )
                attempt_latency = time.perf_counter() - attempt_started
                total_generation_time += attempt_latency

                response = response_raw.choices[0].message.content
                logprobs = response_raw.choices[0].logprobs.token_logprobs if response_raw.choices[0].logprobs else []

                rus_flg = self.is_russian_only(response)
                confidence = self.get_confidence(logprobs)

                usage = extract_usage(response_raw)

                prompt_text = "\n".join([m["content"] for m in messages])
                est_prompt_tokens = estimate_tokens(prompt_text)
                est_completion_tokens = estimate_tokens(response)
                est_total_tokens = est_prompt_tokens + est_completion_tokens

                log_generation_attempt(
                    request_id=request_id,
                    attempt_no=attempt_no,
                    success_flag=1 if (rus_flg and confidence >= conf_thresh) else 0,
                    russian_only_flag=1 if rus_flg else 0,
                    confidence_score=confidence,
                    latency_sec=attempt_latency,
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"],
                    total_tokens=usage["total_tokens"],
                    est_prompt_tokens=est_prompt_tokens,
                    est_completion_tokens=est_completion_tokens,
                    est_total_tokens=est_total_tokens,
                    response_preview=response[:1000]
                )

                if rus_flg is True and confidence >= conf_thresh:
                    success = True
                    final_response = response

                    metrics["pipeline_status"] = "success"
                    metrics["successful_attempt"] = attempt_no
                    metrics["russian_only_flag"] = 1
                    metrics["confidence_score"] = confidence
                    metrics["output_chars"] = len(response)

                    metrics["prompt_tokens"] = usage["prompt_tokens"]
                    metrics["completion_tokens"] = usage["completion_tokens"]
                    metrics["total_tokens"] = usage["total_tokens"]

                    metrics["est_prompt_tokens"] = est_prompt_tokens
                    metrics["est_completion_tokens"] = est_completion_tokens
                    metrics["est_total_tokens"] = est_total_tokens

                    break

            except Exception as e:
                attempt_latency = time.perf_counter() - attempt_started
                total_generation_time += attempt_latency

                log_generation_attempt(
                    request_id=request_id,
                    attempt_no=attempt_no,
                    success_flag=0,
                    russian_only_flag=0,
                    confidence_score=None,
                    latency_sec=attempt_latency,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )

                metrics["error_stage"] = "generation"
                metrics["error_type"] = type(e).__name__
                metrics["error_message"] = str(e)

        metrics["generation_latency_sec"] = total_generation_time
        metrics["total_latency_sec"] = time.perf_counter() - started_at

        if not success:
            metrics["pipeline_status"] = "fallback"
            metrics["output_chars"] = len(final_response)

        return final_response, metrics