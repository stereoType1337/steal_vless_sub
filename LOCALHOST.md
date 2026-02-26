# Запуск на localhost

## Быстрый старт

### 1. Создайте файл `.env`

```bash
cp .env.example .env
```

Отредактируйте `.env` и добавьте ваш Telegram Bot Token:

```env
BOT_TOKEN=your_bot_token_here
DOMAIN=localhost
```

### 2. Запустите бота

**Вариант 1: Используя скрипт (рекомендуется)**

```bash
chmod +x run_local.sh
./run_local.sh
```

**Вариант 2: Вручную**

```bash
# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Создайте файл для vless ссылок
echo "[]" > vless_links.json

# Запустите бота в режиме polling
python server.py --polling
```

## Режимы работы

### Polling режим (для localhost)
Бот будет опрашивать Telegram API на наличие новых сообщений. Это удобно для разработки на localhost.

```bash
python server.py --polling
```

### Webhook режим (для production)
Бот работает через webhook. Требует публичный URL (например, через ngrok).

```bash
python server.py
```

## Использование с ngrok (для webhook режима)

Если вы хотите использовать webhook режим на localhost:

1. Установите ngrok: https://ngrok.com/download
2. Запустите ngrok:
   ```bash
   ngrok http 3022
   ```
3. Скопируйте HTTPS URL (например, `https://abc123.ngrok.io`)
4. Обновите `.env`:
   ```env
   DOMAIN=abc123.ngrok.io
   ```
5. Запустите бота:
   ```bash
   python server.py
   ```

## Доступные endpoints

После запуска бота доступны следующие endpoints:

- `http://localhost:3022/health` - Health check
- `http://localhost:3022/sub` - Получить vless ссылки в base64
- `http://localhost:3022/webhook/` - Webhook для Telegram (только в webhook режиме)

## Остановка

Нажмите `Ctrl+C` для остановки бота.


