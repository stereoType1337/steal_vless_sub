import hashlib
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = aiohttp.ClientTimeout(total=30)


def _loc_id(source_url: str, remarks: str) -> str:
    return hashlib.md5(f"{source_url}{remarks}".encode()).hexdigest()


def parse_configs(raw: str, source_url: str) -> list[dict[str, Any]]:
    """
    Разобрать ответ sub URL.
    Поддерживает:
      - JSON массив объектов:  [{...}, ...]
      - Одиночный JSON объект: {...}
    Возвращает список словарей с ключами: id, name, source_url, config.
    """
    import json

    try:
        data = json.loads(raw)
    except Exception as e:
        logger.error("Ошибка парсинга JSON от %s: %s", source_url, e)
        return []

    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        logger.error("Неожиданный тип JSON от %s: %s", source_url, type(data))
        return []

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        remarks = (
            item.get("remarks")
            or item.get("ps")
            or item.get("name")
            or item.get("tag")
            or ""
        )
        remarks = str(remarks).strip()
        if not remarks:
            # Генерируем имя из хоста если remarks пустые
            remarks = str(item.get("add") or item.get("host") or item.get("server") or "unknown")

        loc_id = _loc_id(source_url, remarks)
        results.append({
            "id": loc_id,
            "name": remarks,
            "source_url": source_url,
            "config": item,
        })

    return results


async def fetch_one(session: aiohttp.ClientSession, url: str) -> tuple[str, str | None]:
    """Fetch одного URL. Возвращает (url, text | None)."""
    try:
        async with session.get(url, timeout=FETCH_TIMEOUT) as resp:
            resp.raise_for_status()
            text = await resp.text()
            return url, text
    except Exception as e:
        logger.error("Ошибка fetch %s: %s", url, e)
        return url, None


async def fetch_all(urls: list[str]) -> list[tuple[str, str | None]]:
    """Конкурентный fetch всех URLs. Возвращает список (url, text | None)."""
    import asyncio

    if not urls:
        return []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)
