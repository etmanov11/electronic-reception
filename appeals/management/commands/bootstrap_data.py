from django.core.management.base import BaseCommand
from appeals.models import Appeal


class Command(BaseCommand):
    help = 'Создаёт статусы и тестовые данные (вызывается из Procfile)'

    def handle(self, *args, **options):
        Appeal.bootstrap_statuses()
        self.stdout.write(self.style.SUCCESS('Статусы инициализированы.'))
