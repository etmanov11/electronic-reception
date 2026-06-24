from django import forms
from appeals.models import Status


class ReportFilterForm(forms.Form):
    """Форма фильтрации данных для формирования отчётов"""

    date_from = forms.DateField(
        label='Период с', required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'дд.мм.гггг'})
    )
    date_to = forms.DateField(
        label='Период по', required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'дд.мм.гггг'})
    )
    status = forms.ModelChoiceField(
        queryset=Status.objects.all().order_by('order'),
        label='Статус', required=False, empty_label='Все статусы',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ChoiceField(
        choices=[
            ('', 'Все категории'),
            ('social', 'Социальная поддержка'),
            ('pension', 'Пенсионные вопросы'),
            ('housing', 'Жилищные вопросы'),
            ('other', 'Иное')
        ],
        label='Категория', required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('Дата начала периода не может быть позже даты окончания.')
        return cleaned_data