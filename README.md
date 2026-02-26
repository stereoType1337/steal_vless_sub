# Vless Bot - Telegram бот для управления vless ссылками

Telegram бот для управления vless ссылками с автоматической отдачей в base64 формате.

## Функционал

- **Актуализировать vless** - обновить список vless ссылок
- **Показать vless** - просмотреть текущие ссылки
- **Получить ссылку** - получить ссылку для подписки в формате `https://domain.ru/sub`

## Установка

### 1. Создайте файл .env

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```
BOT_TOKEN=your_telegram_bot_token
DOMAIN=your_domain.ru
```

### 2. Создайте SSL сертификаты (для тестирования)

Для тестирования создайте самоподписанный сертификат:

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/CN=your_domain.ru"
```

Для продакшена используйте Let's Encrypt сертификаты.

### 3. Запустите через Docker Compose

```bash
docker-compose up -d
```

### 4. Настройте webhook для Telegram бота

После запуска, установите webhook:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your_domain.ru/webhook/"
```

Или используйте скрипт:

```bash
python3 -c "
import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('BOT_TOKEN')
domain = os.getenv('DOMAIN')

response = requests.post(
    f'https://api.telegram.org/bot{token}/setWebhook',
    json={'url': f'https://{domain}/webhook/'}
)
print(response.json())
"
```

## Использование

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Используйте кнопки для управления:
   - **Актуализировать vless** - отправьте vless ссылки (по одной на строку или через запятую)
   - **Показать vless** - просмотрите текущие ссылки
   - **Получить ссылку** - получите ссылку вида `https://domain.ru/sub`

## API Endpoints

- `GET /health` - health check
- `POST /webhook/` - webhook для Telegram
- `GET /sub` - получить vless ссылки в base64 формате
- `GET /sub/<id>` - получить vless ссылки по ID

## Структура проекта

```
vless-bot/
├── server.py              # Основной файл с ботом и Flask сервером
├── requirements.txt       # Python зависимости
├── Dockerfile            # Docker образ
├── docker-compose.yml    # Docker Compose конфигурация
├── nginx.conf           # Nginx конфигурация
├── .env                 # Переменные окружения (создать из .env.example)
├── .env.example         # Пример переменных окружения
├── vless_links.json     # Файл с vless ссылками (создается автоматически)
└── README.md           # Документация
```

## Логи

Просмотр логов:

```bash
docker-compose logs -f vless-bot
```

## Остановка

```bash
docker-compose down
```

## Перезапуск

```bash
docker-compose restart
```

## Удаление

```bash
docker-compose down -v
```

## Безопасность

- Не публикуйте `.env` файл в репозиторий
- Используйте валидные SSL сертификаты для продакшена
- Ограничьте доступ к боту только нужным пользователям

