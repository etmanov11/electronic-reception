# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Указываем модуль настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Загружаем конфигурацию из Django settings с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях
app.autodiscover_tasks()

# Расписание периодических задач (запускается через celery beat)
app.conf.beat_schedule = {
    'check-appeal-deadlines-daily': {
        'task': 'appeals.tasks.check_deadlines',
        'schedule': crontab(hour=8, minute=0),  # Ежедневно в 08:00
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Тестовая задача для проверки работоспособности Celery"""
    print(f'Request: {self.request!r}')