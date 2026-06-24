from django.contrib import admin
from django.utils.html import format_html
from .models import Appeal, Status, Document, AuditLog

class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    readonly_fields = ('uploaded_at',)

@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ('reg_number', 'title', 'author', 'status_colored', 'deadline', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('reg_number', 'title', 'author__username', 'contact_email')
    readonly_fields = ('reg_number', 'created_at', 'closed_at', 'metadata')
    inlines = [DocumentInline]
    date_hierarchy = 'created_at'

    def status_colored(self, obj):
        if not obj.status_id:
            return 'Не задан'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', obj.status.color, obj.status.name)
    status_colored.short_description = 'Статус'

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'order')
    ordering = ('order',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target_model', 'target_id')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('timestamp', 'user', 'action', 'target_model', 'target_id', 'details', 'ip_address')
    search_fields = ('user__username', 'details')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
