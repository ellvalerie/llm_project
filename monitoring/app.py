from dash import Dash, dcc, html, Input, Output
from monitoring.pages.interactions import build_interactions_layout
from monitoring.pages.technical import build_technical_layout

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>RAG Monitoring</title>
        {%favicon%}
        {%css%}
        <style>
            * {
                box-sizing: border-box;
                font-family: Inter, Arial, sans-serif;
            }

            body {
                margin: 0;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #334155 100%);
            }

            .page-wrapper {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 32px;
            }

            .hero-card {
                width: 100%;
                max-width: 1000px;
                background: rgba(255, 255, 255, 0.10);
                backdrop-filter: blur(18px);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 28px;
                padding: 40px;
                box-shadow: 0 25px 70px rgba(0, 0, 0, 0.28);
                color: #f8fafc;
            }

            .hero-badge {
                display: inline-block;
                padding: 8px 14px;
                border-radius: 999px;
                background: rgba(96, 165, 250, 0.18);
                border: 1px solid rgba(147, 197, 253, 0.30);
                color: #bfdbfe;
                font-size: 14px;
                margin-bottom: 18px;
            }

            .hero-title {
                margin: 0 0 12px 0;
                font-size: 44px;
                line-height: 1.1;
            }

            .hero-subtitle {
                margin: 0 0 28px 0;
                color: #cbd5e1;
                font-size: 18px;
                max-width: 760px;
            }

            .content-card {
                background: rgba(15, 23, 42, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 28px;
            }

            .nav-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 18px;
            }

            .nav-card {
                text-decoration: none;
                color: #f8fafc;
                background: linear-gradient(180deg, rgba(30,41,59,0.95) 0%, rgba(15,23,42,0.95) 100%);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 22px;
                padding: 24px;
                min-height: 190px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
                box-shadow: 0 10px 30px rgba(2, 6, 23, 0.25);
            }

            .nav-card:hover {
                transform: translateY(-4px);
                border-color: rgba(96, 165, 250, 0.55);
                box-shadow: 0 18px 40px rgba(59, 130, 246, 0.18);
            }

            .nav-card-title {
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 10px;
            }

            .nav-card-text {
                color: #cbd5e1;
                font-size: 15px;
                line-height: 1.5;
            }

            .nav-card-link {
                color: #93c5fd;
                font-weight: 600;
                margin-top: 20px;
            }

            .placeholder-box {
                border: 1px dashed rgba(148, 163, 184, 0.5);
                border-radius: 20px;
                padding: 28px;
                color: #cbd5e1;
                background: rgba(30,41,59,0.35);
                font-size: 16px;
                line-height: 1.6;
            }

            .back-link {
                display: inline-block;
                margin-top: 18px;
                color: #93c5fd;
                text-decoration: none;
                font-weight: 600;
            }
            .page-top {
                align-items: flex-start;
                padding-top: 28px;
                padding-bottom: 28px;
            }

            .wide-card {
                max-width: 1400px;
            }

            .toolbar-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }

            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
                gap: 18px;
                margin-top: 12px;
                margin-bottom: 24px;
            }

            .metric-card {
                background: linear-gradient(180deg, rgba(30,41,59,0.96) 0%, rgba(15,23,42,0.96) 100%);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 22px;
                padding: 22px;
                box-shadow: 0 12px 30px rgba(2, 6, 23, 0.22);
            }

            .metric-title {
                font-size: 14px;
                color: #93c5fd;
                margin-bottom: 12px;
            }

            .metric-value {
                font-size: 34px;
                font-weight: 800;
                color: #f8fafc;
                line-height: 1.1;
                margin-bottom: 8px;
            }

            .metric-subtitle {
                font-size: 13px;
                color: #94a3b8;
                line-height: 1.5;
            }

            .charts-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px;
                margin-bottom: 18px;
            }

            .single-block {
                display: block;
            }

            .chart-card {
                background: rgba(15, 23, 42, 0.58);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 24px;
                padding: 18px;
                box-shadow: 0 10px 30px rgba(2, 6, 23, 0.18);
            }

            .section-title {
                margin: 4px 0 8px 0;
                font-size: 24px;
                color: #f8fafc;
            }

            .section-subtitle {
                margin: 0 0 18px 0;
                font-size: 14px;
                color: #94a3b8;
            }

            .wordcloud-image {
                width: 100%;
                border-radius: 18px;
                display: block;
            }

            .top-list {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .top-list-row {
                display: flex;
                justify-content: space-between;
                gap: 18px;
                align-items: flex-start;
                padding: 14px 16px;
                border-radius: 16px;
                background: rgba(30,41,59,0.45);
                border: 1px solid rgba(255,255,255,0.06);
            }

            .top-list-question {
                color: #e2e8f0;
                line-height: 1.45;
                font-size: 15px;
                flex: 1;
            }

            .top-list-count {
                color: #93c5fd;
                font-weight: 700;
                font-size: 18px;
                min-width: 28px;
                text-align: right;
            }

            .time-col {
                min-width: 170px;
                font-size: 13px;
                color: #94a3b8;
            }

            .error-row-title {
                color: #f8fafc;
                font-size: 15px;
                font-weight: 700;
                margin-bottom: 4px;
            }

            .error-row-subtitle {
                color: #93c5fd;
                font-size: 13px;
                margin-bottom: 8px;
            }

            .empty-state {
                color: #94a3b8;
                font-size: 15px;
                padding: 16px 4px;
            }

            @media (max-width: 980px) {
                .charts-grid {
                    grid-template-columns: 1fr;
                }

                .hero-title {
                    font-size: 34px;
                }

                .top-list-row {
                    flex-direction: column;
                }

                .time-col {
                    min-width: auto;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


def page_shell(title: str, subtitle: str, children=None):
    children = children or []
    return html.Div(
        className="page-wrapper",
        children=[
            html.Div(
                className="hero-card",
                children=[
                    html.Div("RAG Monitoring", className="hero-badge"),
                    html.H1(title, className="hero-title"),
                    html.P(subtitle, className="hero-subtitle"),
                    html.Div(children, className="content-card"),
                ],
            )
        ],
    )


app.layout = html.Div(
    [
        dcc.Location(id="url"),
        html.Div(id="page-content"),
    ]
)


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname):
    if pathname == "/monitoring/interactions":
        return build_interactions_layout()

    if pathname == "/monitoring/technical":
        return build_technical_layout()

    return page_shell(
        "Мониторинг RAG-агента",
        "Локальный каркас дашборда. На главной странице можно выбрать тип мониторинга и перейти в нужный раздел.",
        [
            html.Div(
                className="nav-grid",
                children=[
                    dcc.Link(
                        className="nav-card",
                        href="/monitoring/interactions",
                        children=[
                            html.Div(
                                [
                                    html.Div("Взаимодействие", className="nav-card-title"),
                                    html.Div(
                                        "Пользовательские метрики: вопросы, пользователи, чаты, реакции, негативные ответы и тематики.",
                                        className="nav-card-text",
                                    ),
                                ]
                            ),
                            html.Div("Перейти →", className="nav-card-link"),
                        ],
                    ),
                    dcc.Link(
                        className="nav-card",
                        href="/monitoring/technical",
                        children=[
                            html.Div(
                                [
                                    html.Div("Технический", className="nav-card-title"),
                                    html.Div(
                                        "Latency, ошибки, стабильность пайплайна, токены и технические метрики модели.",
                                        className="nav-card-text",
                                    ),
                                ]
                            ),
                            html.Div("Перейти →", className="nav-card-link"),
                        ],
                    ),
                ],
            )
        ],
    )


if __name__ == "__main__":
    app.run(debug=False)