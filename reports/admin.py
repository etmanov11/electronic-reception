from django.contrib import admin
from .models import ExportHistory


@admin.register(ExportHistory)
class ExportHistoryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'report_type', 'records_count', 'ip_address')
    list_filter = ('report_type', 'created_at')
    search_fields = ('user__username', 'user__last_name')
    readonly_fields = ('created_at', 'user', 'report_type', 'filters_applied', 'records_count', 'ip_address')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # Записи создаются только программно

    def has_change_permission(self, request, obj=None):
        return False  # Журнал аудита не должен редактироваться
