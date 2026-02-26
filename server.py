import json
import logging

from aiohttp import web

import storage

logger = logging.getLogger(__name__)


async def _handle_sub(request: web.Request) -> web.Response:
    configs = await storage.get_enabled_configs()
    body = json.dumps(configs, ensure_ascii=False)
    return web.Response(
        text=body,
        content_type="application/json",
        charset="utf-8",
    )


async def _handle_health(request: web.Request) -> web.Response:
    return web.Response(text='{"status":"ok"}', content_type="application/json")


def _make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/sub", _handle_sub)
    app.router.add_get("/health", _handle_health)
    return app


async def start_server(host: str, port: int) -> web.AppRunner:
    """Запустить aiohttp сервер в текущем event loop. Возвращает runner для cleanup."""
    app = _make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("HTTP сервер запущен на %s:%d", host, port)
    return runner
