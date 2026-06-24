#!/bin/bash
set -e

# Установка шрифтов для PDF (кириллица)
apt-get update -qq && apt-get install -y -qq fontconfig fonts-dejavu-core fonts-noto 2>/dev/null | tail -5
fc-cache -f

echo ">>> Применение миграций..."
python manage.py migrate --noinput

echo ">>> Сбор статических файлов..."
python manage.py collectstatic --noinput --clear

echo ">>> Загрузка начальных данных..."
python manage.py bootstrap_data || true

echo ">>> Запуск сервера..."
exec gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
