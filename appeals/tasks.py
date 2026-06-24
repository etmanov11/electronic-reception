from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Appeal
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_status_notification(self, appeal_id, status_name, recipient_email):
    """Отправка email-уведомления о смене статуса с автоматическим повтором при ошибке"""
    try:
        subject = f'Изменение статуса обращения {appeal_id}'
        message = f'Ваше обращение изменило статус на: {status_name}.\n\nС уважением, Электронная приемная.'
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient_email], fail_silently=False)
        logger.info(f'Уведомление отправлено для обращения {appeal_id}')
    except Exception as exc:
        logger.error(f'Ошибка отправки уведомления: {exc}')
        raise self.retry(exc=exc, countdown=300)

@shared_task
def check_deadlines():
    """Фоновая проверка просроченных обращений (запускается по расписанию)"""
    today = timezone.now().date()
    overdue = Appeal.objects.filter(deadline__lt=today, closed_at__isnull=True)
    count = overdue.count()
    if count > 0:
        logger.warning(f'Обнаружено {count} просроченных обращений.')
    return f'Проверено дедлайнов. Просрочено: {count}'

