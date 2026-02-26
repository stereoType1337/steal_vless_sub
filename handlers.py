import functools
import logging
import os
from math import ceil

import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import parser as sub_parser
import storage

logger = logging.getLogger(__name__)

PAGE_SIZE = 8

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_id() -> int | None:
    raw = os.getenv("ADMIN_USER_ID", "")
    return int(raw) if raw.strip().isdigit() else None


def admin_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else None
        aid = _admin_id()
        if aid is not None and uid != aid:
            if update.message:
                await update.message.reply_text("⛔ Нет доступа.")
            return
        return await func(update, context)
    return wrapper


async def _do_refresh(urls: list[str]) -> tuple[int, int]:
    """Fetch + parse + upsert. Возвращает (total_locations, failed_urls)."""
    results = await sub_parser.fetch_all(urls)
    total = 0
    failed = 0
    for url, text in results:
        if text is None:
            failed += 1
            continue
        locs = sub_parser.parse_configs(text, url)
        await storage.upsert_locations_bulk(locs)
        total += len(locs)
    return total, failed


def _locations_keyboard(locations: dict, page: int) -> InlineKeyboardMarkup:
    items = list(locations.items())
    total_pages = max(1, ceil(len(items) / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    chunk = items[start: start + PAGE_SIZE]

    rows = []
    for loc_id, loc in chunk:
        icon = "✅" if loc.get("enabled", True) else "❌"
        name = loc.get("name", loc_id)[:40]
        rows.append([
            InlineKeyboardButton(
                f"{icon} {name}",
                callback_data=f"toggle:{loc_id}",
            )
        ])

    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"locations_page:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"locations_page:{page + 1}"))
    rows.append(nav)

    # Enable All / Disable All
    rows.append([
        InlineKeyboardButton("✅ Enable All", callback_data="enable_all"),
        InlineKeyboardButton("❌ Disable All", callback_data="disable_all"),
    ])

    return InlineKeyboardMarkup(rows)


def _subs_keyboard(urls: list[str]) -> InlineKeyboardMarkup:
    import hashlib
    rows = []
    for url in urls:
        uid = hashlib.md5(url.encode()).hexdigest()
        short = url[:40] + "…" if len(url) > 40 else url
        rows.append([InlineKeyboardButton(f"🗑 {short}", callback_data=f"remove_sub:{uid}")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@admin_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pub_host = os.getenv("PUBLIC_HOST", os.getenv("SERVER_HOST", "localhost"))
    port = os.getenv("SERVER_PORT", "8080")
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Команды:\n"
        "/addsub <url> — добавить источник подписки\n"
        "/subs — список источников\n"
        "/refresh — обновить локации\n"
        "/locations — управление локациями\n"
        "/check <host> — проверить страну хоста\n"
        f"/mysub — ваша ссылка на подписку\n\n"
        f"Текущий /sub: `http://{pub_host}:{port}/sub`",
        parse_mode="Markdown",
    )


@admin_only
async def cmd_addsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /addsub <url>")
        return

    url = context.args[0].strip()
    added = await storage.add_sub_url(url)
    if not added:
        await update.message.reply_text("ℹ️ Этот URL уже есть в списке.")
        return

    msg = await update.message.reply_text("⏳ Получаю локации…")
    total, failed = await _do_refresh([url])
    text = f"✅ Добавлено. Найдено {total} локаций."
    if failed:
        text += f"\n⚠️ Ошибок fetch: {failed}"
    await msg.edit_text(text)


@admin_only
async def cmd_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urls = await storage.get_sub_urls()
    if not urls:
        await update.message.reply_text("Список источников пуст. Добавьте через /addsub <url>")
        return
    text = "📋 Источники подписки (нажмите 🗑 чтобы удалить):"
    await update.message.reply_text(text, reply_markup=_subs_keyboard(urls))


@admin_only
async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    urls = await storage.get_sub_urls()
    if not urls:
        await update.message.reply_text("Нет источников. Добавьте через /addsub <url>")
        return
    msg = await update.message.reply_text("⏳ Обновляю…")
    total, failed = await _do_refresh(urls)
    text = f"✅ Обновлено. Локаций: {total}."
    if failed:
        text += f"\n⚠️ Ошибок fetch: {failed}"
    await msg.edit_text(text)


@admin_only
async def cmd_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    locs = await storage.get_all_locations()
    if not locs:
        await update.message.reply_text("Нет локаций. Сначала /addsub <url> и /refresh")
        return
    enabled = sum(1 for l in locs.values() if l.get("enabled", True))
    await update.message.reply_text(
        f"📍 Локации ({enabled}/{len(locs)} включено):",
        reply_markup=_locations_keyboard(locs, 0),
    )


@admin_only
async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /check <host>")
        return
    host = context.args[0].strip()
    msg = await update.message.reply_text(f"⏳ Проверяю {host}…")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://ip-api.com/json/{host}?fields=status,country,countryCode,city,isp,query",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
        if data.get("status") == "success":
            text = (
                f"🌍 {host}\n"
                f"Страна: {data.get('countryCode', '?')} {data.get('country', '?')}\n"
                f"Город: {data.get('city', '?')}\n"
                f"ISP: {data.get('isp', '?')}\n"
                f"IP: {data.get('query', '?')}"
            )
        else:
            text = f"❌ ip-api вернул: {data.get('message', 'ошибка')}"
    except Exception as e:
        text = f"❌ Ошибка: {e}"
    await msg.edit_text(text)


@admin_only
async def cmd_mysub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pub_host = os.getenv("PUBLIC_HOST", os.getenv("SERVER_HOST", "localhost"))
    port = os.getenv("SERVER_PORT", "8080")
    url = f"http://{pub_host}:{port}/sub"
    await update.message.reply_text(
        f"🔗 Ваша ссылка на подписку:\n`{url}`",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Callback query handler
# ---------------------------------------------------------------------------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "noop":
        return

    if data.startswith("toggle:"):
        loc_id = data[len("toggle:"):]
        new_state = await storage.toggle_location(loc_id)
        if new_state is None:
            await query.answer("Локация не найдена", show_alert=True)
            return
        # Обновить клавиатуру на той же странице
        locs = await storage.get_all_locations()
        # Определить текущую страницу по первому элементу видимых кнопок
        page = _current_page_from_markup(query.message.reply_markup, locs)
        enabled = sum(1 for l in locs.values() if l.get("enabled", True))
        await query.edit_message_text(
            f"📍 Локации ({enabled}/{len(locs)} включено):",
            reply_markup=_locations_keyboard(locs, page),
        )

    elif data.startswith("locations_page:"):
        page = int(data[len("locations_page:"):])
        locs = await storage.get_all_locations()
        enabled = sum(1 for l in locs.values() if l.get("enabled", True))
        await query.edit_message_text(
            f"📍 Локации ({enabled}/{len(locs)} включено):",
            reply_markup=_locations_keyboard(locs, page),
        )

    elif data.startswith("remove_sub:"):
        uid = data[len("remove_sub:"):]
        import hashlib
        urls = await storage.get_sub_urls()
        target = next((u for u in urls if hashlib.md5(u.encode()).hexdigest() == uid), None)
        if target:
            await storage.remove_sub_url(target)
            urls = await storage.get_sub_urls()
        if urls:
            await query.edit_message_reply_markup(reply_markup=_subs_keyboard(urls))
        else:
            await query.edit_message_text("Список источников пуст.")

    elif data == "enable_all":
        await storage.set_all_locations(True)
        locs = await storage.get_all_locations()
        enabled = sum(1 for l in locs.values() if l.get("enabled", True))
        await query.edit_message_text(
            f"📍 Локации ({enabled}/{len(locs)} включено):",
            reply_markup=_locations_keyboard(locs, 0),
        )

    elif data == "disable_all":
        await storage.set_all_locations(False)
        locs = await storage.get_all_locations()
        enabled = sum(1 for l in locs.values() if l.get("enabled", True))
        await query.edit_message_text(
            f"📍 Локации ({enabled}/{len(locs)} включено):",
            reply_markup=_locations_keyboard(locs, 0),
        )


def _current_page_from_markup(markup: InlineKeyboardMarkup | None, locs: dict) -> int:
    """Извлечь текущую страницу из callback_data навигационных кнопок."""
    if markup is None:
        return 0
    total_pages = max(1, ceil(len(locs) / PAGE_SIZE))
    for row in markup.inline_keyboard:
        for btn in row:
            cd = btn.callback_data or ""
            if cd.startswith("locations_page:"):
                neighbor = int(cd[len("locations_page:"):])
                # Кнопка ◀️ → текущая = neighbor + 1; кнопка ▶️ → текущая = neighbor - 1
                if btn.text == "◀️":
                    return neighbor + 1
                if btn.text == "▶️":
                    return neighbor - 1
            # Кнопка с "N/M" — сам номер
            if "/" in (btn.text or "") and btn.callback_data == "noop":
                try:
                    return int(btn.text.split("/")[0]) - 1
                except ValueError:
                    pass
    return 0


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("addsub", cmd_addsub))
    app.add_handler(CommandHandler("subs", cmd_subs))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.add_handler(CommandHandler("locations", cmd_locations))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("mysub", cmd_mysub))
    app.add_handler(CallbackQueryHandler(callback_handler))
