from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'department', 'is_verified', 'is_active', 'last_login'
    )
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff', 'department')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'department', 'phone')
    ordering = ('last_name', 'first_name')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Персональные данные'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'position')}),
        (_('Организационные данные'), {'fields': ('role', 'department', 'is_verified')}),
        (_('Права доступа'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Даты'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'department', 'is_verified'),
        }),
    )
    readonly_fields = ('last_login', 'date_joined')

    def save_model(self, request, obj, form, change):
        if not change:  # При создании пользователя автоматически помечаем как active
            obj.is_active = True
        super().save_model(request, obj, form, change)
