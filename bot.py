import asyncio
import logging
import os
import signal

from dotenv import load_dotenv
from telegram.ext import Application

import handlers
import server

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8080"))

    # --- HTTP сервер ---
    runner = await server.start_server(host, port)

    # --- Telegram бот (PTB v21 low-level async API) ---
    app = Application.builder().token(token).build()
    handlers.register_handlers(app)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Бот запущен. Ожидание обновлений…")

    # Ждём SIGINT / SIGTERM
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _stop():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    await stop_event.wait()

    logger.info("Остановка…")
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    await runner.cleanup()
    logger.info("Завершено.")


if __name__ == "__main__":
    asyncio.run(main())
