from django.contrib.auth.models import UserManager
from django.db import models


class CustomUserManager(UserManager):
    """Кастомный менеджер для расширенных запросов к пользователям"""

    def get_queryset(self):
        return super().get_queryset().select_related()

    def active_staff(self):
        """Возвращает активных сотрудников учреждения"""
        return self.filter(is_active=True).exclude(role='citizen')

    def citizens(self):
        """Возвращает только граждан (заявителей)"""
        return self.filter(role='citizen', is_active=True)