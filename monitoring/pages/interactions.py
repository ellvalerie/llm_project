import base64
import io
import re
import sqlite3
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import dcc, html
from matplotlib import pyplot as plt
from wordcloud import WordCloud
from dotenv import load_dotenv

import os 
load_dotenv()

DATABASE = os.getenv("DATABASE", "data/users_data.db")


DB_PATH = Path(DATABASE)

NEGATIVE_PATTERNS = [
    "не знаю",
    "не могу",
    "недостаточно данных",
    "не найдено",
    "не удалось",
    "нет информации",
    "не смог",
    "не получится",
    "не располагаю информацией",
    "не удалось", 
    "не обладаю достаточной информацией"
]

STOPWORDS_RU = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
    "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
    "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет",
    "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли", "если",
    "уже", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять",
    "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они",
    "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была",
    "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
    "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем",
    "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "сейчас",
    "были", "куда", "зачем", "сказать", "всех", "никогда", "сегодня", "можно",
    "при", "наконец", "два", "об", "другой", "хоть", "после", "над", "больше",
    "тот", "через", "эти", "нас", "про", "них", "какая", "много", "разве",
    "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой", "перед", "иногда",
    "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда", "конечно",
    "всю", "между",
    "где", "мой", "заказ", "когда", "можно", "ли", "как", "почему", "есть",
    "это", "этот", "нужно", "хочу", "узнать", "посмотреть",
}

PLOTLY_TEMPLATE = "plotly_dark"


def get_connection():
    return sqlite3.connect(DB_PATH)


def load_data():
    conn = get_connection()
    queries = pd.read_sql_query("SELECT * FROM users_queries", conn)
    chats = pd.read_sql_query("SELECT * FROM users_chats", conn)
    conn.close()

    if not queries.empty:
        queries["query_dttm"] = pd.to_datetime(queries["query_dttm"], errors="coerce")
        queries["reaction_dttm"] = pd.to_datetime(queries["reaction_dttm"], errors="coerce")
        queries["query_txt"] = queries["query_txt"].fillna("")
        queries["answer_txt"] = queries["answer_txt"].fillna("")

    if not chats.empty:
        chats["user_id"] = chats["user_id"].astype(str)
        chats["chat_id"] = chats["chat_id"].astype(str)

    return queries, chats


def mark_negative_answers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df["is_negative"] = []
        return df

    pattern = "|".join(re.escape(p) for p in NEGATIVE_PATTERNS)
    df = df.copy()
    df["is_negative"] = df["answer_txt"].str.lower().str.contains(pattern, na=False)
    return df


def extract_keywords(texts, top_n=15):
    all_text = " ".join(texts).lower()
    words = re.findall(r"[а-яa-zё]{3,}", all_text)

    filtered = [w for w in words if w not in STOPWORDS_RU]
    counter = Counter(filtered)
    return counter.most_common(top_n), counter


def make_wordcloud_base64(counter: Counter):
    if not counter:
        return None

    wc = WordCloud(
        width=1200,
        height=500,
        background_color="#0f172a",
        colormap="Blues",
        max_words=80,
    ).generate_from_frequencies(counter)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_facecolor("#0f172a")

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)

    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def kpi_card(title, value, subtitle=""):
    return html.Div(
        className="metric-card",
        children=[
            html.Div(title, className="metric-title"),
            html.Div(value, className="metric-value"),
            html.Div(subtitle, className="metric-subtitle"),
        ],
    )


def build_interactions_layout():
    queries, chats = load_data()
    queries = mark_negative_answers(queries)

    total_questions = int(len(queries))

    avg_chats_per_user = 0
    if not chats.empty:
        avg_chats_per_user = chats.groupby("user_id")["chat_id"].nunique().mean()

    avg_negative_per_user = 0
    negative_share = 0
    if not queries.empty:
        neg_by_user = queries.groupby("user_id")["is_negative"].sum()
        avg_negative_per_user = neg_by_user.mean()
        negative_share = queries["is_negative"].mean() * 100

    avg_reaction = 0
    reaction_count = 0
    if not queries.empty:
        reaction_series = pd.to_numeric(queries["like_flg"], errors="coerce").dropna()
        if not reaction_series.empty:
            avg_reaction = reaction_series.mean()
            reaction_count = len(reaction_series)

    # Динамика вопросов по дням
    fig_questions_by_day = px.line()
    if not queries.empty and queries["query_dttm"].notna().any():
        daily = (
            queries.dropna(subset=["query_dttm"])
            .assign(date=lambda x: x["query_dttm"].dt.date)
            .groupby("date")
            .size()
            .reset_index(name="questions_cnt")
        )
        fig_questions_by_day = px.line(
            daily,
            x="date",
            y="questions_cnt",
            markers=True,
            title="Динамика количества вопросов по дням",
            template=PLOTLY_TEMPLATE,
        )
        fig_questions_by_day.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # Реакции
    fig_reactions = px.bar()
    if not queries.empty:
        reactions = (
            queries["like_flg"]
            .fillna("Нет реакции")
            .replace({1: "Лайк", 0: "Нейтрально", -1: "Дизлайк"})
            .value_counts()
            .reset_index()
        )
        reactions.columns = ["reaction", "count"]

        fig_reactions = px.bar(
            reactions,
            x="reaction",
            y="count",
            title="Распределение реакций пользователей",
            template=PLOTLY_TEMPLATE,
            text="count",
        )
        fig_reactions.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # Топ ключевых слов
    top_keywords, keyword_counter = extract_keywords(queries["query_txt"].tolist() if not queries.empty else [], top_n=15)
    fig_keywords = px.bar()
    if top_keywords:
        keywords_df = pd.DataFrame(top_keywords, columns=["word", "count"])
        fig_keywords = px.bar(
            keywords_df,
            x="count",
            y="word",
            orientation="h",
            title="Топ ключевых слов в вопросах",
            template=PLOTLY_TEMPLATE,
            text="count",
        )
        fig_keywords.update_layout(
            yaxis=dict(categoryorder="total ascending"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=60, b=20),
        )

    # Облако слов
    wordcloud_src = make_wordcloud_base64(keyword_counter)

    # Топ вопросов
    top_questions_block = html.Div("Нет данных")
    if not queries.empty:
        top_questions = (
            queries["query_txt"]
            .value_counts()
            .head(8)
            .reset_index()
        )
        top_questions.columns = ["question", "count"]

        top_questions_block = html.Div(
            className="top-list",
            children=[
                html.Div(
                    className="top-list-row",
                    children=[
                        html.Div(row["question"], className="top-list-question"),
                        html.Div(str(row["count"]), className="top-list-count"),
                    ],
                )
                for _, row in top_questions.iterrows()
            ],
        )

    return html.Div(
        className="page-wrapper page-top",
        children=[
            html.Div(
                className="hero-card wide-card",
                children=[
                    html.Div("RAG Monitoring", className="hero-badge"),
                    html.H1("Мониторинг взаимодействия", className="hero-title"),
                    html.P(
                        "Страница показывает активность пользователей, качество ответов и основные темы запросов к RAG-агенту.",
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
                            kpi_card(
                                "Кол-во вопросов боту",
                                f"{total_questions:,}".replace(",", " "),
                                "Все записи из users_queries",
                            ),
                            kpi_card(
                                "Среднее число чатов на пользователя",
                                f"{avg_chats_per_user:.2f}",
                                "На основе users_chats",
                            ),
                            kpi_card(
                                "Среднее число негативных ответов",
                                f"{avg_negative_per_user:.2f}",
                                f"Доля негативных ответов: {negative_share:.1f}%",
                            ),
                            kpi_card(
                                "Средняя реакция like_flg",
                                f"{avg_reaction:.2f}",
                                f"Учтено реакций: {reaction_count}",
                            ),
                        ],
                    ),

                    html.Div(
                        className="charts-grid",
                        children=[
                            html.Div(
                                className="chart-card",
                                children=[dcc.Graph(figure=fig_questions_by_day, config={"displayModeBar": False})],
                            ),
                            html.Div(
                                className="chart-card",
                                children=[dcc.Graph(figure=fig_reactions, config={"displayModeBar": False})],
                            ),
                        ],
                    ),

                    html.Div(
                        className="charts-grid",
                        children=[
                            html.Div(
                                className="chart-card",
                                children=[dcc.Graph(figure=fig_keywords, config={"displayModeBar": False})],
                            ),
                            html.Div(
                                className="chart-card",
                                children=[
                                    html.H3("Облако тем и ключевых слов", className="section-title"),
                                    html.P(
                                        "Построено по всем вопросам пользователей из поля query_txt.",
                                        className="section-subtitle",
                                    ),
                                    html.Img(src=wordcloud_src, className="wordcloud-image") if wordcloud_src else html.Div("Нет данных")
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
                                    html.H3("Топ повторяющихся вопросов", className="section-title"),
                                    html.P(
                                        "Полезно для поиска самых частых пользовательских сценариев.",
                                        className="section-subtitle",
                                    ),
                                    top_questions_block,
                                ],
                            )
                        ],
                    ),
                ],
            )
        ],
    )