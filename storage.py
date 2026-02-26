import asyncio
import json
import os
from typing import Any

DATA_FILE = os.getenv("DATA_FILE", "data.json")
_lock = asyncio.Lock()

_DEFAULT: dict[str, Any] = {"sub_urls": [], "locations": {}}


def _load_sync() -> dict[str, Any]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sub_urls": [], "locations": {}}


async def _load() -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _load_sync)


async def _save(data: dict[str, Any]) -> None:
    tmp = DATA_FILE + ".tmp"

    def _write():
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write)


# --- Sub URLs ---

async def add_sub_url(url: str) -> bool:
    """Добавить sub URL. Возвращает True если добавлен (не было дубля)."""
    async with _lock:
        data = await _load()
        if url in data["sub_urls"]:
            return False
        data["sub_urls"].append(url)
        await _save(data)
        return True


async def remove_sub_url(url: str) -> bool:
    """Удалить sub URL. Возвращает True если был удалён."""
    async with _lock:
        data = await _load()
        if url not in data["sub_urls"]:
            return False
        data["sub_urls"].remove(url)
        await _save(data)
        return True


async def get_sub_urls() -> list[str]:
    async with _lock:
        data = await _load()
        return list(data["sub_urls"])


# --- Locations ---

async def upsert_location(loc_id: str, name: str, source_url: str, config: dict) -> None:
    """Сохранить/обновить локацию, сохраняя enabled при refresh."""
    async with _lock:
        data = await _load()
        existing = data["locations"].get(loc_id, {})
        enabled = existing.get("enabled", True)
        data["locations"][loc_id] = {
            "name": name,
            "source_url": source_url,
            "config": config,
            "enabled": enabled,
        }
        await _save(data)


async def upsert_locations_bulk(locations: list[dict]) -> None:
    """
    Bulk-upsert локаций для данного source_url.
    Каждый элемент: {id, name, source_url, config}.
    Сохраняет enabled при refresh. Удаляет старые локации этого source_url
    которых нет в новом списке.
    """
    async with _lock:
        data = await _load()
        if not locations:
            await _save(data)
            return

        source_url = locations[0]["source_url"]
        new_ids = {loc["id"] for loc in locations}

        # Удалить устаревшие локации от того же source_url
        to_delete = [
            lid for lid, ldata in data["locations"].items()
            if ldata.get("source_url") == source_url and lid not in new_ids
        ]
        for lid in to_delete:
            del data["locations"][lid]

        for loc in locations:
            existing = data["locations"].get(loc["id"], {})
            enabled = existing.get("enabled", True)
            data["locations"][loc["id"]] = {
                "name": loc["name"],
                "source_url": loc["source_url"],
                "config": loc["config"],
                "enabled": enabled,
            }
        await _save(data)


async def toggle_location(loc_id: str) -> bool | None:
    """Переключить enabled. Возвращает новое состояние или None если не найдено."""
    async with _lock:
        data = await _load()
        if loc_id not in data["locations"]:
            return None
        new_val = not data["locations"][loc_id]["enabled"]
        data["locations"][loc_id]["enabled"] = new_val
        await _save(data)
        return new_val


async def set_all_locations(enabled: bool) -> None:
    """Включить или выключить все локации."""
    async with _lock:
        data = await _load()
        for loc in data["locations"].values():
            loc["enabled"] = enabled
        await _save(data)


async def get_all_locations() -> dict[str, dict]:
    async with _lock:
        data = await _load()
        return dict(data["locations"])


async def get_enabled_configs() -> list[dict]:
    """Вернуть конфиги всех включённых локаций."""
    async with _lock:
        data = await _load()
        return [
            loc["config"]
            for loc in data["locations"].values()
            if loc.get("enabled", True)
        ]
