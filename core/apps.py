from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = _('Управление пользователями и аутентификацией')

    def ready(self):
        # Регистрация сигналов (при необходимости)
        import core.signals  # noqa: F401
