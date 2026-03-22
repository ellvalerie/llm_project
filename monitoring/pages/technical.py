import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import dcc, html
import plotly.graph_objects as go
from dotenv import load_dotenv

import os
load_dotenv()



TECH_DB_PATH = Path(os.getenv("TECH_DATABASE", "data/tech.db"))
PLOTLY_TEMPLATE = "plotly_dark"


def get_connection():
    return sqlite3.connect(TECH_DB_PATH)


def load_tech_data():
    conn = get_connection()
    metrics = pd.read_sql_query("SELECT * FROM tech_metrics", conn)
    attempts = pd.read_sql_query("SELECT * FROM tech_generation_attempts", conn)
    conn.close()

    if not metrics.empty:
        metrics["created_at"] = pd.to_datetime(metrics["created_at"], errors="coerce")

    if not attempts.empty:
        attempts["created_at"] = pd.to_datetime(attempts["created_at"], errors="coerce")

    return metrics, attempts


def format_num(value, digits=2):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}f}"

def empty_figure(title="Нет данных"):
    fig = go.Figure()
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Нет данных для отображения",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=16),
            )
        ],
    )
    return fig


def kpi_card(title, value, subtitle=""):
    return html.Div(
        className="metric-card",
        children=[
            html.Div(title, className="metric-title"),
            html.Div(value, className="metric-value"),
            html.Div(subtitle, className="metric-subtitle"),
        ],
    )


def build_error_list(errors_df: pd.DataFrame):
    if errors_df.empty:
        return html.Div("Ошибок не найдено", className="empty-state")

    rows = []
    for _, row in errors_df.iterrows():
        created_at = row.get("created_at")
        created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(created_at) else "—"

        rows.append(
            html.Div(
                className="top-list-row",
                children=[
                    html.Div(
                        [
                            html.Div(
                                f"{row.get('pipeline_status', '—')} · {row.get('error_stage', '—')}",
                                className="error-row-title",
                            ),
                            html.Div(
                                f"{row.get('error_type', '—')}",
                                className="error-row-subtitle",
                            ),
                            html.Div(
                                (row.get("error_message") or "Без текста ошибки")[:220],
                                className="top-list-question",
                            ),
                        ],
                    ),
                    html.Div(created_at_str, className="top-list-count time-col"),
                ],
            )
        )

    return html.Div(className="top-list", children=rows)


def build_technical_layout():
    metrics, attempts = load_tech_data()

    total_requests = len(metrics)

    success_rate = 0
    fallback_rate = 0
    error_rate = 0
    avg_total_latency = None
    avg_generation_latency = None
    avg_confidence = None
    first_attempt_success_rate = 0
    avg_total_tokens = None
    avg_attempts_per_request = None

    if not metrics.empty:
        success_rate = (metrics["pipeline_status"].eq("success")).mean() * 100
        fallback_rate = (metrics["pipeline_status"].eq("fallback")).mean() * 100
        error_rate = (metrics["pipeline_status"].eq("error")).mean() * 100

        avg_total_latency = pd.to_numeric(metrics["total_latency_sec"], errors="coerce").mean()
        avg_generation_latency = pd.to_numeric(metrics["generation_latency_sec"], errors="coerce").mean()
        avg_confidence = pd.to_numeric(metrics["confidence_score"], errors="coerce").mean()

        avg_total_tokens = pd.to_numeric(
            metrics["total_tokens"].fillna(metrics["est_total_tokens"]),
            errors="coerce"
        ).mean()

        first_attempt_success_rate = (
            metrics["successful_attempt"].eq(1).fillna(False).mean() * 100
        )

        avg_attempts_per_request = pd.to_numeric(metrics["generation_attempts"], errors="coerce").mean()

    # 1. Динамика запросов по дням
    fig_requests_by_day = empty_figure("Динамика технических запросов по дням")
    if not metrics.empty and metrics["created_at"].notna().any():
        daily = (
            metrics.dropna(subset=["created_at"])
            .assign(date=lambda x: x["created_at"].dt.date)
            .groupby("date")
            .size()
            .reset_index(name="requests_cnt")
        )

        fig_requests_by_day = px.line(
            daily,
            x="date",
            y="requests_cnt",
            markers=True,
            title="Динамика технических запросов по дням",
            template=PLOTLY_TEMPLATE,
        )
        fig_requests_by_day.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # 2. Статусы пайплайна
    fig_status = empty_figure("Распределение статусов пайплайна")
    if not metrics.empty:
        status_df = (
            metrics["pipeline_status"]
            .fillna("unknown")
            .value_counts()
            .reset_index()
        )
        status_df.columns = ["pipeline_status", "count"]

        fig_status = px.pie(
            status_df,
            names="pipeline_status",
            values="count",
            title="Распределение статусов пайплайна",
            template=PLOTLY_TEMPLATE,
            hole=0.45,
        )
        fig_status.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # 3. Latency по этапам
    fig_latency = empty_figure("Средняя latency по этапам, сек")
    if not metrics.empty:
        latency_data = pd.DataFrame({
            "stage": [
                "total_latency_sec",
                "retrieval_latency_sec",
                "generation_latency_sec",
                "db_write_latency_sec",
                "send_latency_sec",
            ],
            "value": [
                pd.to_numeric(metrics["total_latency_sec"], errors="coerce").mean(),
                pd.to_numeric(metrics["retrieval_latency_sec"], errors="coerce").mean(),
                pd.to_numeric(metrics["generation_latency_sec"], errors="coerce").mean(),
                pd.to_numeric(metrics["db_write_latency_sec"], errors="coerce").mean(),
                pd.to_numeric(metrics["send_latency_sec"], errors="coerce").mean(),
            ],
        })

        latency_data["stage_label"] = [
            "Total",
            "Retrieval",
            "Generation",
            "DB write",
            "Send",
        ]

        fig_latency = px.bar(
            latency_data,
            x="stage_label",
            y="value",
            title="Средняя latency по этапам, сек",
            template=PLOTLY_TEMPLATE,
            text="value",
        )
        fig_latency.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_latency.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # 4. Ошибки по stage
    fig_error_stage = empty_figure("Топ этапов, где происходят ошибки")
    if not metrics.empty:
        err = metrics[metrics["pipeline_status"].eq("error")].copy()
        if not err.empty:
            err_stage = (
                err["error_stage"]
                .fillna("unknown")
                .value_counts()
                .reset_index()
            )
            err_stage.columns = ["error_stage", "count"]

            fig_error_stage = px.bar(
                err_stage,
                x="count",
                y="error_stage",
                orientation="h",
                title="Топ этапов, где происходят ошибки",
                template=PLOTLY_TEMPLATE,
                text="count",
            )
            fig_error_stage.update_layout(
                yaxis=dict(categoryorder="total ascending"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=60, b=20),
            )

    # 5. Confidence
    fig_confidence = empty_figure("Распределение confidence score")
    if not metrics.empty and metrics["confidence_score"].notna().any():
        conf_df = metrics.dropna(subset=["confidence_score"]).copy()
        fig_confidence = px.histogram(
            conf_df,
            x="confidence_score",
            nbins=20,
            title="Распределение confidence score",
            template=PLOTLY_TEMPLATE,
        )
        fig_confidence.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # 6. Токены по дням
    fig_tokens = empty_figure("Суммарные токены по дням")
    if not metrics.empty and metrics["created_at"].notna().any():
        metrics_tokens = metrics.copy()
        metrics_tokens["tokens_final"] = pd.to_numeric(
            metrics_tokens["total_tokens"].fillna(metrics_tokens["est_total_tokens"]),
            errors="coerce",
        )

        token_daily = (
            metrics_tokens.dropna(subset=["created_at"])
            .assign(date=lambda x: x["created_at"].dt.date)
            .groupby("date", as_index=False)["tokens_final"]
            .sum()
        )

        if not token_daily.empty:
            fig_tokens = px.line(
                token_daily,
                x="date",
                y="tokens_final",
                markers=True,
                title="Суммарные токены по дням",
                template=PLOTLY_TEMPLATE,
            )
            fig_tokens.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=60, b=20),
            )

    # 7. Попытки генерации
    fig_attempt_success = empty_figure("Успешность по номеру попытки, %")
    if not attempts.empty:
        attempts_local = attempts.copy()
        attempts_local["success_label"] = attempts_local["success_flag"].map({1: "Успех", 0: "Неуспех"}).fillna("Неизвестно")
        attempt_stat = (
            attempts_local.groupby("attempt_no")["success_flag"]
            .mean()
            .reset_index()
        )
        if not attempt_stat.empty:
            attempt_stat["success_rate"] = attempt_stat["success_flag"] * 100

            fig_attempt_success = px.bar(
                attempt_stat,
                x="attempt_no",
                y="success_rate",
                title="Успешность по номеру попытки, %",
                template=PLOTLY_TEMPLATE,
                text="success_rate",
            )
            fig_attempt_success.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig_attempt_success.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=60, b=20),
            )

    # 8. Топ моделей
    top_models_block = html.Div("Нет данных", className="empty-state")
    if not metrics.empty:
        model_df = (
            metrics["llm_model"]
            .fillna("unknown")
            .value_counts()
            .head(8)
            .reset_index()
        )
        model_df.columns = ["llm_model", "count"]

        top_models_block = html.Div(
            className="top-list",
            children=[
                html.Div(
                    className="top-list-row",
                    children=[
                        html.Div(row["llm_model"], className="top-list-question"),
                        html.Div(str(row["count"]), className="top-list-count"),
                    ],
                )
                for _, row in model_df.iterrows()
            ],
        )

    # 9. Последние ошибки
    latest_errors_block = html.Div("Нет данных", className="empty-state")
    if not metrics.empty:
        latest_errors = (
            metrics[
                metrics["pipeline_status"].eq("error") |
                metrics["error_type"].notna() |
                metrics["error_message"].notna()
            ]
            .sort_values("created_at", ascending=False)
            .head(8)
        )
        latest_errors_block = build_error_list(latest_errors)

    return html.Div(
        className="page-wrapper page-top",
        children=[
            html.Div(
                className="hero-card wide-card",
                children=[
                    html.Div("RAG Monitoring", className="hero-badge"),
                    html.H1("Технический мониторинг", className="hero-title"),
                    html.P(
                        "Здесь собраны метрики производительности пайплайна, статусы обработки, ошибки, confidence, токены и попытки генерации.",
                        className="hero-subtitle",
                    ),

                    html.Div(
                        className="toolbar-row",
                        children=[
                            dcc.Link("← Назад на главную", href="/", className="back-link"),
                        ],
                    ),

                    html.Div(
                        className="metrics-grid",
                        children=[
                            kpi_card("Кол-во технических запросов", f"{total_requests:,}".replace(",", " "), "Все записи из tech_metrics"),
                            kpi_card("Success rate", f"{success_rate:.1f}%", "Доля запросов со статусом success"),
                            kpi_card("Fallback rate", f"{fallback_rate:.1f}%", "Доля запросов со статусом fallback"),
                            kpi_card("Error rate", f"{error_rate:.1f}%", "Доля запросов со статусом error"),
                            kpi_card("Средняя total latency", f"{format_num(avg_total_latency)} сек", "Общий пайплайн"),
                            kpi_card("Средняя generation latency", f"{format_num(avg_generation_latency)} сек", "LLM-генерация"),
                            kpi_card("Средний confidence", format_num(avg_confidence), "Итоговая confidence_score"),
                            kpi_card("Успешно с 1 попытки", f"{first_attempt_success_rate:.1f}%", "successful_attempt = 1"),
                            kpi_card("Средние токены", format_num(avg_total_tokens), "total_tokens / est_total_tokens"),
                            kpi_card("Среднее число попыток", format_num(avg_attempts_per_request), "generation_attempts"),
                        ],
                    ),

                    html.Div(
                        className="charts-grid",
                        children=[
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_requests_by_day, config={"displayModeBar": False})]),
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_status, config={"displayModeBar": False})]),
                        ],
                    ),

                    html.Div(
                        className="charts-grid",
                        children=[
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_latency, config={"displayModeBar": False})]),
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_error_stage, config={"displayModeBar": False})]),
                        ],
                    ),

                    html.Div(
                        className="charts-grid",
                        children=[
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_confidence, config={"displayModeBar": False})]),
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_tokens, config={"displayModeBar": False})]),
                        ],
                    ),

                    html.Div(
                        className="charts-grid",
                        children=[
                            html.Div(className="chart-card", children=[dcc.Graph(figure=fig_attempt_success, config={"displayModeBar": False})]),
                            html.Div(
                                className="chart-card",
                                children=[
                                    html.H3("Топ LLM-моделей", className="section-title"),
                                    html.P("Какие модели чаще всего использовались в пайплайне.", className="section-subtitle"),
                                    top_models_block,
                                ],
                            ),
                        ],
                    ),

                    html.Div(
                        className="single-block",
                        children=[
                            html.Div(
                                className="chart-card",
                                children=[
                                    html.H3("Последние ошибки и проблемные кейсы", className="section-title"),
                                    html.P(
                                        "Последние записи, где пайплайн завершился ошибкой или были заполнены error_type / error_message.",
                                        className="section-subtitle",
                                    ),
                                    latest_errors_block,
                                ],
                            )
                        ],
                    ),
                ],
            )
        ],
    )