from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Расширенная модель пользователя с ролевой моделью и организационными полями"""

    ROLE_CHOICES = [
        ('citizen', _('Гражданин')),
        ('operator', _('Оператор приёмной')),
        ('executor', _('Исполнитель')),
        ('manager', _('Руководитель подразделения')),
        ('admin', _('Администратор системы')),
    ]

    role = models.CharField(
        _('Роль пользователя'), max_length=20, choices=ROLE_CHOICES,
        default='citizen', db_index=True
    )
    department = models.CharField(_('Подразделение'), max_length=150, blank=True, null=True)
    position = models.CharField(_('Должность'), max_length=150, blank=True, null=True)
    phone = models.CharField(_('Контактный телефон'), max_length=18, blank=True)
    is_verified = models.BooleanField(
        _('Подтверждён'), default=False,
        help_text=_('Указывает, прошла ли учётная запись верификацию сотрудником учреждения.')
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['last_name', 'first_name']
        permissions = [
            ('can_manage_users', 'Может управлять учётными записями'),
            ('can_view_audit_logs', 'Может просматривать журнал аудита'),
        ]

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name} ({self.get_role_display()})" if full_name else self.username

    def is_staff_member(self):
        """Проверяет, является ли пользователь сотрудником учреждения"""
        return self.role in ['operator', 'executor', 'manager', 'admin']

    @property
    def role_display(self):
        return self.get_role_display()