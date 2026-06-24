import csv
import io
import os
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib import messages
from appeals.models import Appeal
from .forms import ReportFilterForm
from .models import ExportHistory


_ARIAL_PATH = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf')
_ARIALBD_PATH = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arialbd.ttf')
_FONT_NAME = None


def _ensure_font():
    global _FONT_NAME
    if _FONT_NAME:
        return _FONT_NAME
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        if os.path.exists(_ARIAL_PATH):
            pdfmetrics.registerFont(TTFont('CyrFont', _ARIAL_PATH))
            if os.path.exists(_ARIALBD_PATH):
                pdfmetrics.registerFont(TTFont('CyrFont-Bold', _ARIALBD_PATH))
            _FONT_NAME = 'CyrFont'
            return _FONT_NAME
    except Exception:
        pass
    _FONT_NAME = 'Helvetica'
    return _FONT_NAME


def _apply_filters(queryset, form_data):
    """Вспомогательная функция для фильтрации QuerySet обращений"""
    if form_data.get('date_from'):
        queryset = queryset.filter(created_at__date__gte=form_data['date_from'])
    if form_data.get('date_to'):
        queryset = queryset.filter(created_at__date__lte=form_data['date_to'])
    if form_data.get('status'):
        queryset = queryset.filter(status=form_data['status'])
    if form_data.get('category'):
        queryset = queryset.filter(category=form_data['category'])
    return queryset


def _check_report_access(user):
    """Проверка прав доступа к отчётности (сотрудники, руководители и администраторы)"""
    return user.is_authenticated and user.role in ['operator', 'executor', 'manager', 'admin']


def _build_dashboard_context(form):
    queryset = Appeal.objects.select_related('status', 'author', 'executor').all()
    filtered_data = form.cleaned_data if form.is_valid() else {}
    filtered_qs = _apply_filters(queryset, filtered_data)

    stats = {
        'total': filtered_qs.count(),
        'approved': filtered_qs.filter(status__code='approved').count(),
        'rejected': filtered_qs.filter(status__code='rejected').count(),
        'in_progress': filtered_qs.filter(status__code__in=['in_progress', 'on_review']).count(),
        'by_category': filtered_qs.values('category').annotate(count=Count('id')).order_by('-count'),
        'avg_processing_days': None,
    }

    closed = filtered_qs.filter(closed_at__isnull=False)
    if closed.exists():
        days_diff = [(a.closed_at.date() - a.created_at.date()).days for a in closed]
        stats['avg_processing_days'] = sum(days_diff) / len(days_diff) if days_diff else 0

    return {
        'form': form,
        'stats': stats,
        'recent_appeals': filtered_qs.order_by('-created_at')[:10],
    }


@login_required
@user_passes_test(_check_report_access, login_url='/accounts/login/')
def report_dashboard(request):
    """Панель аналитики и визуализации статистики"""
    form = ReportFilterForm(request.GET)
    context = _build_dashboard_context(form)
    return render(request, 'reports/dashboard.html', context)


@login_required
@user_passes_test(_check_report_access)
def export_csv(request):
    """Экспорт отфильтрованных данных в CSV с кодировкой UTF-8 (поддержка кириллицы)"""
    form = ReportFilterForm(request.GET)
    if not form.is_valid():
        messages.error(request, 'Ошибка в параметрах фильтрации.')
        return render(request, 'reports/dashboard.html', _build_dashboard_context(form))

    queryset = Appeal.objects.select_related('status', 'author', 'executor').order_by('-created_at')
    filtered_qs = _apply_filters(queryset, form.cleaned_data)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        'Рег. номер', 'Дата подачи', 'Автор', 'Категория', 'Статус',
        'Исполнитель', 'Срок рассмотрения', 'Дата закрытия'
    ])

    for appeal in filtered_qs:
        writer.writerow([
            appeal.reg_number,
            appeal.created_at.strftime('%d.%m.%Y'),
            f"{appeal.author.last_name} {appeal.author.first_name}",
            appeal.get_category_display(),
            appeal.status.name,
            f"{appeal.executor.last_name} {appeal.executor.first_name}" if appeal.executor else 'Не назначен',
            appeal.deadline.strftime('%d.%m.%Y') if appeal.deadline else '-',
            appeal.closed_at.strftime('%d.%m.%Y %H:%M') if appeal.closed_at else '-'
        ])

    csv_content = '\ufeff' + output.getvalue()
    response = HttpResponse(csv_content.encode('utf-8'), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="appeals_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

    # Фиксация экспорта в журнале аудита
    ExportHistory.objects.create(
        user=request.user, report_type='csv', filters_applied=request.GET.dict(),
        records_count=filtered_qs.count(), ip_address=request.META.get('REMOTE_ADDR')
    )
    messages.success(request, f'Сформирован отчёт CSV ({filtered_qs.count()} записей).')
    return response


@login_required
@user_passes_test(_check_report_access)
def export_pdf(request):
    """Экспорт отчёта в PDF через reportlab напрямую"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        messages.error(request, 'Модуль PDF-генерации недоступен. Обратитесь к администратору для установки reportlab.')
        fallback_form = ReportFilterForm(request.GET or None)
        return render(request, 'reports/dashboard.html', _build_dashboard_context(fallback_form))

    font_name = _ensure_font()

    form = ReportFilterForm(request.GET)
    if not form.is_valid():
        messages.error(request, 'Ошибка в параметрах фильтрации.')
        return render(request, 'reports/dashboard.html', _build_dashboard_context(form))

    queryset = Appeal.objects.select_related('status', 'author', 'executor').order_by('-created_at')
    filtered_qs = _apply_filters(queryset, form.cleaned_data)

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    title_style = ParagraphStyle('Title', fontName=font_name, fontSize=14, alignment=1, spaceAfter=6)
    date_style = ParagraphStyle('Date', fontName=font_name, fontSize=9, alignment=1, textColor=colors.grey, spaceAfter=12)
    cell_style = ParagraphStyle('Cell', fontName=font_name, fontSize=8, leading=10)
    header_style = ParagraphStyle('Header', fontName=font_name, fontSize=8, leading=10, textColor=colors.white)

    elements = []
    elements.append(Paragraph('Отчёт по обращениям граждан', title_style))
    elements.append(Paragraph(f'Дата формирования: {timezone.now().strftime("%d.%m.%Y %H:%M")}', date_style))

    header = [
        Paragraph('Рег. номер', header_style),
        Paragraph('Тема', header_style),
        Paragraph('Категория', header_style),
        Paragraph('Статус', header_style),
        Paragraph('Дата подачи', header_style),
        Paragraph('Срок', header_style),
    ]
    data = [header]

    for appeal in filtered_qs:
        data.append([
            Paragraph(appeal.reg_number, cell_style),
            Paragraph(appeal.title[:50], cell_style),
            Paragraph(appeal.get_category_display(), cell_style),
            Paragraph(appeal.status.name or '-', cell_style),
            Paragraph(appeal.created_at.strftime('%d.%m.%Y'), cell_style),
            Paragraph(appeal.deadline.strftime('%d.%m.%Y') if appeal.deadline else '-', cell_style),
        ])

    if len(data) == 1:
        data.append([Paragraph('Записи отсутствуют', cell_style)] * 6)

    col_widths = [70, 180, 100, 80, 70, 70]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    footer_style = ParagraphStyle('Footer', fontName=font_name, fontSize=7, alignment=1, textColor=colors.grey, spaceBefore=20)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph('ГКУ СО Самарского округа | Система «Электронная приёмная» | Документ сформирован автоматически', footer_style))

    doc.build(elements)

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="appeals_report_{timezone.now().strftime("%Y%m%d")}.pdf"'

    ExportHistory.objects.create(
        user=request.user, report_type='pdf', filters_applied=request.GET.dict(),
        records_count=filtered_qs.count(), ip_address=request.META.get('REMOTE_ADDR')
    )
    return response
