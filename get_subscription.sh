#!/bin/bash

# Скрипт для получения vless ссылок локально

echo "🔗 Получение vless ссылок..."
echo ""

# Пытаемся получить через Flask endpoint
if curl -s http://localhost:3022/sub > /dev/null 2>&1; then
    echo "✅ Получено через Flask endpoint:"
    echo ""
    curl -s http://localhost:3022/sub
    echo ""
    echo ""
    echo "📋 Скопируйте эту строку и вставьте в ваш клиент"
else
    echo "⚠️  Flask сервер не запущен. Используем файл напрямую:"
    echo ""
    cat vless_links.json | python3 -c "import sys, json, base64; links = json.load(sys.stdin); print(base64.b64encode('\n'.join(links).encode()).decode())"
    echo ""
    echo ""
    echo "📋 Скопируйте эту строку и вставьте в ваш клиент"
fi


