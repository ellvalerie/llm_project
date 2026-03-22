# tech_metrics.py
# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any


DEFAULT_TECH_DB = os.getenv("TECH_DATABASE", "data/tech.db")


def _get_connection(db_path: Optional[str] = None):
    path = db_path or DEFAULT_TECH_DB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return sqlite3.connect(path)


def safe_int(value):
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def estimate_tokens(text: Optional[str]) -> Optional[int]:
    """
    Грубая эвристика.
    Для русского текста часто можно брать ~ 1 токен на 3-4 символа.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def extract_usage(response_raw) -> Dict[str, Optional[int]]:
    """
    Пытаемся вытащить usage из ответа HF клиента.
    Если usage нет, вернем None.
    """
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None

    try:
        usage = getattr(response_raw, "usage", None)
        if usage is not None:
            prompt_tokens = safe_int(getattr(usage, "prompt_tokens", None))
            completion_tokens = safe_int(getattr(usage, "completion_tokens", None))
            total_tokens = safe_int(getattr(usage, "total_tokens", None))
    except Exception:
        pass

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def log_pipeline_metrics(
    request_id: str,
    created_at: str,
    user_id: Optional[str] = None,
    chat_id: Optional[str] = None,
    query_id: Optional[str] = None,
    question_text: Optional[str] = None,
    pipeline_status: Optional[str] = None,
    error_stage: Optional[str] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    traceback_text: Optional[str] = None,
    total_latency_sec: Optional[float] = None,
    retrieval_latency_sec: Optional[float] = None,
    generation_latency_sec: Optional[float] = None,
    db_write_latency_sec: Optional[float] = None,
    send_latency_sec: Optional[float] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    retrieval_k: Optional[int] = None,
    retrieved_docs_count: Optional[int] = None,
    generation_attempts: Optional[int] = None,
    successful_attempt: Optional[int] = None,
    russian_only_flag: Optional[int] = None,
    confidence_score: Optional[float] = None,
    confidence_threshold: Optional[float] = None,
    input_chars: Optional[int] = None,
    output_chars: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    est_prompt_tokens: Optional[int] = None,
    est_completion_tokens: Optional[int] = None,
    est_total_tokens: Optional[int] = None,
    db_path: Optional[str] = None,
):
    try:
        connection = _get_connection(db_path)
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO tech_metrics (
                request_id, user_id, chat_id, query_id, question_text, created_at,
                pipeline_status, error_stage, error_type, error_message, traceback_text,
                total_latency_sec, retrieval_latency_sec, generation_latency_sec, db_write_latency_sec, send_latency_sec,
                llm_provider, llm_model,
                retrieval_k, retrieved_docs_count,
                generation_attempts, successful_attempt, russian_only_flag, confidence_score, confidence_threshold,
                input_chars, output_chars,
                prompt_tokens, completion_tokens, total_tokens,
                est_prompt_tokens, est_completion_tokens, est_total_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, user_id, chat_id, query_id, question_text, created_at,
            pipeline_status, error_stage, error_type, error_message, traceback_text,
            safe_float(total_latency_sec), safe_float(retrieval_latency_sec), safe_float(generation_latency_sec),
            safe_float(db_write_latency_sec), safe_float(send_latency_sec),
            llm_provider, llm_model,
            safe_int(retrieval_k), safe_int(retrieved_docs_count),
            safe_int(generation_attempts), safe_int(successful_attempt), safe_int(russian_only_flag),
            safe_float(confidence_score), safe_float(confidence_threshold),
            safe_int(input_chars), safe_int(output_chars),
            safe_int(prompt_tokens), safe_int(completion_tokens), safe_int(total_tokens),
            safe_int(est_prompt_tokens), safe_int(est_completion_tokens), safe_int(est_total_tokens)
        ))

        connection.commit()
        connection.close()
    except Exception as e:
        print(f"[TECH_METRICS][ERROR] log_pipeline_metrics failed: {e}")


def log_generation_attempt(
    request_id: str,
    attempt_no: int,
    created_at: Optional[str] = None,
    success_flag: Optional[int] = None,
    russian_only_flag: Optional[int] = None,
    confidence_score: Optional[float] = None,
    latency_sec: Optional[float] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    est_prompt_tokens: Optional[int] = None,
    est_completion_tokens: Optional[int] = None,
    est_total_tokens: Optional[int] = None,
    response_preview: Optional[str] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    db_path: Optional[str] = None,
):
    try:
        connection = _get_connection(db_path)
        cursor = connection.cursor()

        if created_at is None:
            created_at = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO tech_generation_attempts (
                request_id, attempt_no, created_at,
                success_flag, russian_only_flag, confidence_score,
                latency_sec,
                prompt_tokens, completion_tokens, total_tokens,
                est_prompt_tokens, est_completion_tokens, est_total_tokens,
                response_preview, error_type, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, safe_int(attempt_no), created_at,
            safe_int(success_flag), safe_int(russian_only_flag), safe_float(confidence_score),
            safe_float(latency_sec),
            safe_int(prompt_tokens), safe_int(completion_tokens), safe_int(total_tokens),
            safe_int(est_prompt_tokens), safe_int(est_completion_tokens), safe_int(est_total_tokens),
            response_preview, error_type, error_message
        ))

        connection.commit()
        connection.close()
    except Exception as e:
        print(f"[TECH_METRICS][ERROR] log_generation_attempt failed: {e}")