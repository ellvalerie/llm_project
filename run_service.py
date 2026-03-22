import asyncio
import threading
import time

from monitoring import app
import llmbot


def run_bot():
    asyncio.run(llmbot.main())


def run_app():
    # Важно: без debug и без reloader,
    # иначе Dash может поднимать лишние процессы
    try:
        app.app.run(debug=False, use_reloader=False, host="0.0.0.0", port=8050)
    except TypeError:
        # Для старых версий Dash
        app.app.run_server(debug=False, use_reloader=False, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    time.sleep(1)

    run_app()