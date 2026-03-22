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

current_dir = os.path.dirname(os.path.abspath(__file__)) 
index_path = os.path.join(current_dir, "faiss_index")

class ResponseGenerator:

    def __init__(self, hf_token, model = "Qwen/Qwen2.5-7B-Instruct", system_prompt = None):
        self.client = InferenceClient(model=model, token=hf_token)

        embeddings  = HuggingFaceEmbeddings(
            model_name="deepvk/USER-base",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

        self.vector_store = FAISS.load_local(
            index_path, embeddings, allow_dangerous_deserialization=True
        )

        if system_prompt == None:
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
        return context
    
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
        return response_raw


    def is_russian_only(self, response):
        pattern = re.compile(r'^[а-яё0-9\s\d.,!?;:()"-]+$', re.IGNORECASE)
        return bool(pattern.match(response))
    
    def get_confidence(self, logprobs):
        logprobs = sum(logprobs) / len(logprobs)
        return math.exp(logprobs)

    def generate(self, question, max_tokens = 3000, conf_thresh = 0.75):
        success = False
        final_response = 'Я не обладаю достаточной информацией для ответа на данный вопрос. Пожалуйста, проконсультируйтесь с квалицицированным специалистом.'

        # Слишком длинные тексты - подозрение на взлом, сразу выдаем заглушку
        if len(question)> 1000:
            return final_response 

        context = self.get_context(question = question, k=10)
        final_response = ''

        # Даем 3 попытки сформировать адекватный ответ
        for trial in range(3):
            response_raw = self.get_response(question = question, context = context, max_tokens = max_tokens)
            response = response_raw.choices[0].message.content
            logprobs = response_raw.choices[0].logprobs.token_logprobs

            rus_flg = self.is_russian_only(response)
            confidence = self.get_confidence(logprobs)

            # Ответ считаем успешным только если он полностью на русском языке и модель в нем уверена
            if rus_flg == True and confidence >= conf_thresh:
                success = True
                break

        if success == True:
            final_response = response

        return final_response