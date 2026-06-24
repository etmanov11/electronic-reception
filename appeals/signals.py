from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appeal, Document, AuditLog

@receiver(post_save, sender=Appeal)
def log_appeal_changes(sender, instance, created, **kwargs):
    if created:
        action = 'CREATE'
        details = f'Создано обращение {instance.reg_number}'
    else:
        action = 'UPDATE'
        details = f'Обновлено обращение {instance.reg_number}'
    AuditLog.objects.create(
        user=instance.author, action=action, target_model='Appeal', target_id=instance.pk, details=details
    )

@receiver(post_save, sender=Document)
def log_document_upload(sender, instance, created, **kwargs):
    if created:
        AuditLog.objects.create(
            user=instance.appeal.author, action='UPDATE', target_model='Document', target_id=instance.pk,
            details=f'Загружен документ к {instance.appeal.reg_number}'
        )