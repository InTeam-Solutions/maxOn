#!/bin/bash

set -e  # Остановить при ошибке

echo "🔐 Авторизация в GitHub Container Registry..."
echo "Введите ваш GitHub токен:"
read -s GITHUB_TOKEN

echo "$GITHUB_TOKEN" | docker login ghcr.io -u 0stg0t --password-stdin

echo ""
echo "🔨 Сборка всех образов..."
docker compose build

echo ""
echo "📤 Загрузка образов в GHCR..."
docker compose push

echo ""
echo "✅ Готово! Все образы загружены в GitHub Container Registry"
echo ""
echo "📋 На другом устройстве выполните:"
echo "   1. Скопируйте docker-compose.yml и .env"
echo "   2. Скопируйте папку ./shared (если нужна)"
echo "   3. Выполните: ./pull.sh"
echo "   4. Запустите: docker-compose up -d"
