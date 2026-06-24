from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from appeals.models import AuditLog
from .models import CustomUser
import logging

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Фиксация входа пользователя в журнал аудита"""
    try:
        AuditLog.objects.create(
            user=user,
            action='LOGIN',
            target_model='CustomUser',
            target_id=user.id,
            details=f'Успешный вход с IP: {request.META.get("REMOTE_ADDR")}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    except Exception as e:
        logger.error(f'Ошибка логирования входа: {e}')


@receiver(post_save, sender=CustomUser)
def log_user_changes(sender, instance, created, **kwargs):
    """Логирование создания/изменения учётных записей"""
    if created:
        action = 'CREATE'
        details = f'Создана учётная запись: {instance.username} (Роль: {instance.role})'
    else:
        action = 'UPDATE'
        details = f'Изменена учётная запись: {instance.username}'

    try:
        AuditLog.objects.create(
            user=instance, action=action, target_model='CustomUser',
            target_id=instance.id, details=details
        )
    except Exception as e:
        logger.error(f'Ошибка логирования пользователя: {e}')