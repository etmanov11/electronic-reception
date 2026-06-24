from django.db import models, transaction
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from core.models import CustomUser  # Предполагается наличие приложения core с кастомной моделью


class Status(models.Model):
    code = models.CharField('Код статуса', max_length=30, unique=True, db_index=True)
    name = models.CharField('Название', max_length=50)
    color = models.CharField('Цвет (CSS класс)', max_length=20, default='secondary')
    order = models.PositiveSmallIntegerField('Порядок отображения', default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Статус'
        verbose_name_plural = 'Статусы'

    def __str__(self):
        return self.name


class Appeal(models.Model):
    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_ON_REVIEW = 'on_review'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_REVISION = 'revision'
    STATUS_CLOSED = 'closed'

    STATUS_SEQUENCE = [
        STATUS_NEW,
        STATUS_IN_PROGRESS,
        STATUS_ON_REVIEW,
        STATUS_REVISION,
        STATUS_APPROVED,
        STATUS_REJECTED,
        STATUS_CLOSED,
    ]
    TERMINAL_STATUSES = {STATUS_CLOSED}
    WORK_STATUSES = {STATUS_IN_PROGRESS, STATUS_ON_REVIEW, STATUS_REVISION}
    REVIEW_DECISION_STATUSES = {STATUS_APPROVED, STATUS_REJECTED}
    STATUS_TRANSITIONS = {
        STATUS_NEW: [STATUS_IN_PROGRESS, STATUS_REJECTED],
        STATUS_IN_PROGRESS: [STATUS_ON_REVIEW, STATUS_APPROVED, STATUS_REJECTED, STATUS_REVISION],
        STATUS_ON_REVIEW: [STATUS_APPROVED, STATUS_REJECTED, STATUS_REVISION],
        STATUS_REVISION: [STATUS_IN_PROGRESS, STATUS_REJECTED],
        STATUS_APPROVED: [STATUS_CLOSED],
        STATUS_REJECTED: [STATUS_CLOSED],
        STATUS_CLOSED: [],
    }
    STATUS_LABELS = {
        STATUS_NEW: 'Зарегистрировано',
        STATUS_IN_PROGRESS: 'В работе',
        STATUS_ON_REVIEW: 'На проверке',
        STATUS_REVISION: 'На доработке',
        STATUS_APPROVED: 'Удовлетворено',
        STATUS_REJECTED: 'Отказано',
        STATUS_CLOSED: 'Закрыто',
    }

    DEFAULT_DEADLINE_DAYS = 30

    author = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='authored_appeals', verbose_name='Автор')
    executor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_appeals', verbose_name='Исполнитель')
    status = models.ForeignKey(Status, on_delete=models.PROTECT, verbose_name='Текущий статус')
    reg_number = models.CharField('Регистрационный номер', max_length=20, unique=True, editable=False, db_index=True)
    title = models.CharField('Тема обращения', max_length=200)
    description = models.TextField('Текст обращения')
    category = models.CharField('Категория', max_length=50, choices=[
        ('social', 'Социальная поддержка'),
        ('pension', 'Пенсионные вопросы'),
        ('housing', 'Жилищные вопросы'),
        ('other', 'Иное')
    ], default='other')
    contact_email = models.EmailField('Контактный email', db_index=True)
    contact_phone = models.CharField('Контактный телефон', max_length=18, blank=True)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    deadline = models.DateField('Срок рассмотрения', null=True, blank=True)
    closed_at = models.DateTimeField('Дата закрытия', null=True, blank=True)
    metadata = models.JSONField('Дополнительные метаданные', blank=True, null=True, default=dict, help_text='Гибкое хранение специфичных параметров')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Обращение'
        verbose_name_plural = 'Обращения'
        permissions = [
            ('can_reassign', 'Может переназначать обращения'),
            ('can_export_data', 'Может экспортировать данные'),
        ]

    @classmethod
    def get_status_by_code(cls, code):
        return Status.objects.get(code=code)

    @classmethod
    def bootstrap_statuses(cls):
        defaults = [
            (cls.STATUS_NEW, 'Новое', 'secondary', 10),
            (cls.STATUS_IN_PROGRESS, 'В работе', 'warning', 20),
            (cls.STATUS_ON_REVIEW, 'На проверке', 'info', 30),
            (cls.STATUS_REVISION, 'На доработке', 'primary', 40),
            (cls.STATUS_APPROVED, 'Удовлетворено', 'success', 50),
            (cls.STATUS_REJECTED, 'Отказано', 'danger', 60),
            (cls.STATUS_CLOSED, 'Закрыто', 'dark', 70),
        ]
        for code, name, color, order in defaults:
            Status.objects.update_or_create(
                code=code,
                defaults={'name': name, 'color': color, 'order': order}
            )

    def save(self, *args, **kwargs):
        if not self.deadline:
            self.deadline = timezone.now().date() + timezone.timedelta(days=self.DEFAULT_DEADLINE_DAYS)

        if not self.status_id:
            try:
                self.status = self.get_status_by_code(self.STATUS_NEW)
            except Status.DoesNotExist as exc:
                raise ValidationError('Не найден обязательный стартовый статус "new".') from exc

        if self.status and self.status.code in self.TERMINAL_STATUSES and not self.closed_at:
            self.closed_at = timezone.now()
        elif self.status and self.status.code not in self.TERMINAL_STATUSES:
            self.closed_at = None

        if self.pk or self.reg_number:
            super().save(*args, **kwargs)
            return

        year = timezone.now().strftime('%Y')
        prefix = f'ER-{year}-'

        for _ in range(10):
            with transaction.atomic():
                last_for_year = (
                    Appeal.objects.select_for_update()
                    .filter(reg_number__startswith=prefix)
                    .order_by('-reg_number')
                    .first()
                )
                last_number = 0
                if last_for_year and last_for_year.reg_number:
                    try:
                        last_number = int(last_for_year.reg_number.rsplit('-', 1)[-1])
                    except (TypeError, ValueError):
                        last_number = 0

                self.reg_number = f'{prefix}{last_number + 1:04d}'
                try:
                    super().save(*args, **kwargs)
                    return
                except Exception as exc:
                    if 'unique' not in str(exc).lower() or 'reg_number' not in str(exc).lower():
                        raise

        raise ValidationError('Не удалось сгенерировать уникальный регистрационный номер обращения.')

    def get_allowed_transition_codes(self, user):
        if not user or not user.is_authenticated:
            return []
        current_code = self.status.code
        candidates = self.STATUS_TRANSITIONS.get(current_code, [])
        return [code for code in candidates if self.can_change_status(code, user)]

    def can_change_status(self, new_status_code, user):
        if not user or not user.is_authenticated:
            return False
        if not self.status_id:
            return False
        allowed = self.STATUS_TRANSITIONS.get(self.status.code, [])
        if new_status_code not in allowed:
            return False
        user_role = user.role
        if new_status_code in [self.STATUS_IN_PROGRESS, self.STATUS_ON_REVIEW] and user_role not in ['operator', 'executor', 'manager', 'admin']:
            return False
        if new_status_code in [self.STATUS_APPROVED, self.STATUS_REJECTED] and user_role not in ['operator', 'manager', 'executor', 'admin']:
            return False
        return True

    def transition_to(self, new_status, actor, comment=''):
        if isinstance(new_status, Status):
            target_status = new_status
        else:
            target_status = self.get_status_by_code(new_status)

        if not self.can_change_status(target_status.code, actor):
            raise ValidationError('Переход в данный статус запрещён правилами или вашими правами.')

        old_status = self.status
        self.status = target_status

        if target_status.code in self.WORK_STATUSES and not self.executor_id:
            self.executor = actor

        if target_status.code in self.TERMINAL_STATUSES and not self.closed_at:
            self.closed_at = timezone.now()

        self.save(update_fields=['status', 'executor', 'closed_at'])

        AuditLog.objects.create(
            user=actor,
            action='STATUS_CHANGE',
            target_model='Appeal',
            target_id=self.id,
            details=f'Изменён с "{old_status.name}" на "{target_status.name}". {comment}',
        )
        return old_status, target_status

    @property
    def workflow_steps(self):
        return [
            {'code': code, 'label': self.STATUS_LABELS[code], 'is_terminal': code in self.TERMINAL_STATUSES}
            for code in self.STATUS_SEQUENCE
        ]

    def __str__(self):
        return f"{self.reg_number} | {self.title}"


class Document(models.Model):
    appeal = models.ForeignKey(Appeal, on_delete=models.CASCADE, related_name='documents', verbose_name='Обращение')
    file = models.FileField(
        'Файл',
        upload_to='appeals/%Y/%m/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'png', 'zip'])]
    )
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)
    description = models.CharField('Описание', max_length=150, blank=True)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

    def __str__(self):
        return f"Документ к {self.appeal.reg_number}"


class AuditLog(models.Model):
    ACTION_TYPES = (
        ('CREATE', 'Создание'),
        ('UPDATE', 'Изменение'),
        ('STATUS_CHANGE', 'Смена статуса'),
        ('DELETE', 'Удаление'),
        ('LOGIN', 'Вход в систему'),
        ('EXPORT', 'Экспорт данных'),
    )
    timestamp = models.DateTimeField('Дата и время', auto_now_add=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь')
    action = models.CharField('Тип действия', max_length=20, choices=ACTION_TYPES)
    target_model = models.CharField('Сущность', max_length=50)
    target_id = models.PositiveIntegerField('ID объекта')
    details = models.TextField('Описание действия', blank=True)
    ip_address = models.GenericIPAddressField('IP-адрес', null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Запись журнала аудита'
        verbose_name_plural = 'Журнал аудита'

    def __str__(self):
        return f"{self.timestamp} | {self.get_action_display()} | {self.target_model}:{self.target_id}"
