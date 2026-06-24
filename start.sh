#!/bin/bash
set -e

echo ">>> Применение миграций..."
python manage.py migrate --noinput

echo ">>> Сбор статических файлов..."
python manage.py collectstatic --noinput

echo ">>> Загрузка начальных данных..."
python manage.py bootstrap_data || true

echo ">>> Запуск сервера..."
exec gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
