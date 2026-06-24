from django.db import models
from core.models import CustomUser


class ExportHistory(models.Model):
    """Журнал сформированных отчётов для аудита и контроля использования данных"""

    REPORT_TYPES = [('csv', 'CSV (табличный)'), ('pdf', 'PDF (печатный)')]

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь')
    report_type = models.CharField('Тип отчёта', max_length=10, choices=REPORT_TYPES)
    filters_applied = models.JSONField('Применённые фильтры', blank=True, null=True, default=dict)
    records_count = models.PositiveIntegerField('Количество записей', default=0)
    created_at = models.DateTimeField('Дата формирования', auto_now_add=True)
    ip_address = models.GenericIPAddressField('IP-адрес', null=True, blank=True)

    class Meta:
        verbose_name = 'Запись экспорта'
        verbose_name_plural = 'Журнал экспорта'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at.strftime('%d.%m.%Y %H:%M')} | {self.get_report_type_display()} | {self.user}"
