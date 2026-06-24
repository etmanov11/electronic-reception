web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py bootstrap_data
