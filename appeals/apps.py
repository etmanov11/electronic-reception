from django.apps import AppConfig

class AppealsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appeals'
    verbose_name = 'Обращения граждан'

    def ready(self):
        import appeals.signals
        # Автоматическая регистрация сигналов при загрузке приложения

