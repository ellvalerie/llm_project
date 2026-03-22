# # # init_tech_db.py
# # # -*- coding: utf-8 -*-

# # import os
# # import sqlite3

# # DB_PATH = os.path.join("data", "tech.db")


# # def init_db():
# #     os.makedirs("data", exist_ok=True)

# #     connection = sqlite3.connect(DB_PATH)
# #     cursor = connection.cursor()

# #     # Основная таблица: одна запись на один запрос пользователя / один прогон пайплайна
# #     cursor.execute("""
# #         CREATE TABLE IF NOT EXISTS tech_metrics (
# #             id INTEGER PRIMARY KEY AUTOINCREMENT,
# #             request_id TEXT NOT NULL,
# #             user_id TEXT,
# #             chat_id TEXT,
# #             query_id TEXT,
# #             question_text TEXT,

# #             created_at TEXT NOT NULL,

# #             pipeline_status TEXT,              -- success / error / fallback
# #             error_stage TEXT,                  -- validation / retrieval / generation / send_message / db / unknown
# #             error_type TEXT,
# #             error_message TEXT,
# #             traceback_text TEXT,

# #             total_latency_sec REAL,
# #             retrieval_latency_sec REAL,
# #             generation_latency_sec REAL,
# #             db_write_latency_sec REAL,
# #             send_latency_sec REAL,

# #             llm_provider TEXT,
# #             llm_model TEXT,

# #             retrieval_k INTEGER,
# #             retrieved_docs_count INTEGER,

# #             generation_attempts INTEGER,
# #             successful_attempt INTEGER,
# #             russian_only_flag INTEGER,         -- 1/0
# #             confidence_score REAL,
# #             confidence_threshold REAL,

# #             input_chars INTEGER,
# #             output_chars INTEGER,

# #             prompt_tokens INTEGER,
# #             completion_tokens INTEGER,
# #             total_tokens INTEGER,

# #             est_prompt_tokens INTEGER,
# #             est_completion_tokens INTEGER,
# #             est_total_tokens INTEGER
# #         )
# #     """)

# #     # Таблица по попыткам генерации: удобно смотреть нестабильность модели
# #     cursor.execute("""
# #         CREATE TABLE IF NOT EXISTS tech_generation_attempts (
# #             id INTEGER PRIMARY KEY AUTOINCREMENT,
# #             request_id TEXT NOT NULL,
# #             attempt_no INTEGER NOT NULL,
# #             created_at TEXT NOT NULL,

# #             success_flag INTEGER,              -- 1/0
# #             russian_only_flag INTEGER,         -- 1/0
# #             confidence_score REAL,

# #             latency_sec REAL,

# #             prompt_tokens INTEGER,
# #             completion_tokens INTEGER,
# #             total_tokens INTEGER,

# #             est_prompt_tokens INTEGER,
# #             est_completion_tokens INTEGER,
# #             est_total_tokens INTEGER,

# #             response_preview TEXT,
# #             error_type TEXT,
# #             error_message TEXT
# #         )
# #     """)

# #     # Индексы
# #     cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_metrics_request_id ON tech_metrics(request_id)")
# #     cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_metrics_created_at ON tech_metrics(created_at)")
# #     cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_metrics_pipeline_status ON tech_metrics(pipeline_status)")
# #     cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_generation_attempts_request_id ON tech_generation_attempts(request_id)")

# #     connection.commit()
# #     connection.close()

# #     print(f"tech.db created successfully at: {DB_PATH}")


# # if __name__ == "__main__":
# #     init_db()

# # check_tech_db.py
# import sqlite3
# import pandas as pd

# db_path = "data/tech.db"

# conn = sqlite3.connect(db_path)

# print("=== Таблицы ===")
# tables = pd.read_sql_query(
#     "SELECT name FROM sqlite_master WHERE type='table';",
#     conn
# )
# print(tables)

# print("\n=== tech_metrics: последние 10 строк ===")
# df_metrics = pd.read_sql_query(
#     """
#     SELECT *
#     FROM tech_metrics
#     ORDER BY id DESC
#     LIMIT 10
#     """,
#     conn
# )
# print(df_metrics)

# print("\n=== tech_generation_attempts: последние 20 строк ===")
# df_attempts = pd.read_sql_query(
#     """
#     SELECT *
#     FROM tech_generation_attempts
#     ORDER BY id DESC
#     LIMIT 20
#     """,
#     conn
# )
# print(df_attempts)

# conn.close()

import sqlite3
from pathlib import Path


USERS_DB = Path("data/users_data.db")


def clear_users_db(db_path: Path):
    if not db_path.exists():
        print(f"[users_data.db] Файл не найден: {db_path.resolve()}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DELETE FROM users_queries")
    cur.execute("DELETE FROM users_chats")

    conn.commit()
    conn.close()

    print("[users_data.db] Таблицы users_queries и users_chats очищены.")


if __name__ == "__main__":
    clear_users_db(USERS_DB)
    print("Готово: базы очищены.")