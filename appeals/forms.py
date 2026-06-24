from django import forms
from django.core.validators import RegexValidator
from django.utils import timezone
from .models import Appeal, Document, Status

PHONE_REGEX = RegexValidator(r'^\+?[\d\s\-()]{10,18}$', 'Введите корректный номер телефона (10-18 цифр).')


class AppealCreateForm(forms.ModelForm):
    contact_phone = forms.CharField(
        label='Контактный телефон',
        validators=[PHONE_REGEX],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'})
    )
    contact_email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.ru'})
    )

    class Meta:
        model = Appeal
        fields = ['title', 'description', 'category', 'contact_email', 'contact_phone']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Кратко опишите суть обращения'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Подробное описание ситуации...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_contact_email(self):
        email = self.cleaned_data['contact_email']
        today = timezone.now().date()
        exists = Appeal.objects.filter(contact_email=email, created_at__date=today).exists()
        if exists:
            raise forms.ValidationError('С этим email уже зарегистрировано обращение сегодня.')
        return email


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Описание вложения'}),
        }


class StatusUpdateForm(forms.Form):
    new_status = forms.ModelChoiceField(
        queryset=Status.objects.none(),
        label='Новый статус',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        label='Комментарий к изменению',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False
    )

    def __init__(self, *args, appeal=None, user=None, **kwargs):
        self.appeal = appeal
        self.user = user
        super().__init__(*args, **kwargs)
        if appeal and user:
            allowed_codes = appeal.get_allowed_transition_codes(user)
            self.fields['new_status'].queryset = Status.objects.filter(code__in=allowed_codes).order_by('order')
        else:
            self.fields['new_status'].queryset = Status.objects.none()

    def clean_new_status(self):
        new_status = self.cleaned_data['new_status']
        if not self.appeal or not self.user:
            raise forms.ValidationError('Контекст смены статуса не задан.')
        if not self.appeal.can_change_status(new_status.code, self.user):
            raise forms.ValidationError('Переход в данный статус запрещён правилами или вашими правами.')
        return new_status
