from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Appeal, Document, Status
from .forms import AppealCreateForm, DocumentUploadForm, StatusUpdateForm


def is_staff_or_manager(user):
    return user.is_authenticated and user.role in ['operator', 'executor', 'manager', 'admin']


def can_access_appeal(user, appeal):
    if not user.is_authenticated:
        return False
    if user.role == 'citizen':
        return appeal.author_id == user.id
    if user.role == 'executor':
        return appeal.executor_id == user.id or appeal.executor_id is None
    return user.role in ['operator', 'manager', 'admin']


@login_required
def appeal_list(request):
    queryset = Appeal.objects.select_related('status', 'author', 'executor').all()

    if request.user.role == 'citizen':
        queryset = queryset.filter(author=request.user)
    elif request.user.role == 'executor':
        queryset = queryset.filter(Q(executor=request.user) | Q(executor__isnull=True))

    status_filter = request.GET.get('status')
    search_query = request.GET.get('q')
    if status_filter:
        queryset = queryset.filter(status__code=status_filter)
    if search_query:
        queryset = queryset.filter(Q(title__icontains=search_query) | Q(reg_number__icontains=search_query))

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'appeals/appeal_list.html', {
        'page_obj': page_obj,
        'statuses': Status.objects.all()
    })


@login_required
def appeal_create(request):
    if request.method == 'POST':
        form = AppealCreateForm(request.POST)
        if form.is_valid():
            appeal = form.save(commit=False)
            appeal.author = request.user
            try:
                appeal.save()
            except ValidationError as exc:
                form.add_error(None, exc.message)
            else:
                messages.success(request, f'Обращение зарегистрировано. Номер: {appeal.reg_number}')
                return redirect('appeals:detail', pk=appeal.pk)
    else:
        form = AppealCreateForm()
    return render(request, 'appeals/appeal_form.html', {'form': form})


@login_required
def appeal_detail(request, pk):
    appeal = get_object_or_404(Appeal.objects.select_related('status', 'author', 'executor'), pk=pk)

    if not can_access_appeal(request.user, appeal):
        messages.error(request, 'У вас нет прав для просмотра этого обращения.')
        return redirect('appeals:list')

    documents = appeal.documents.all()
    allowed_transitions = appeal.get_allowed_transition_codes(request.user)

    status_form = None
    if is_staff_or_manager(request.user):
        status_form = StatusUpdateForm(appeal=appeal, user=request.user)

    return render(request, 'appeals/appeal_detail.html', {
        'appeal': appeal,
        'documents': documents,
        'status_form': status_form,
        'allowed_transitions': allowed_transitions,
        'statuses': Status.objects.all().order_by('order'),
        'workflow_steps': appeal.workflow_steps,
    })


@require_POST
@login_required
def update_status(request, pk):
    appeal = get_object_or_404(Appeal.objects.select_related('status', 'author', 'executor'), pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not can_access_appeal(request.user, appeal) or not is_staff_or_manager(request.user):
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Доступ запрещён.'}, status=403)
        messages.error(request, 'Доступ запрещён.')
        return redirect('appeals:list')

    form = StatusUpdateForm(request.POST, appeal=appeal, user=request.user)
    if form.is_valid():
        new_status = form.cleaned_data['new_status']
        try:
            _, target_status = appeal.transition_to(
                new_status=new_status,
                actor=request.user,
                comment=form.cleaned_data.get('comment', '')
            )
        except ValidationError as exc:
            message = exc.message
            if is_ajax:
                return JsonResponse({'success': False, 'message': message}, status=400)
            messages.error(request, message)
        else:
            messages.success(request, f'Статус изменён на: {target_status.name}')
            if is_ajax:
                allowed_statuses = Status.objects.filter(code__in=appeal.get_allowed_transition_codes(request.user)).order_by('order')
                return JsonResponse({
                    'success': True,
                    'status': target_status.code,
                    'status_name': target_status.name,
                    'color': target_status.color,
                    'allowed_next': appeal.get_allowed_transition_codes(request.user),
                    'workflow_steps': appeal.workflow_steps,
                    'allowed_choices': [
                        {'id': status.id, 'code': status.code, 'name': status.name}
                        for status in allowed_statuses
                    ],
                })
    else:
        message = 'Ошибка валидации формы.'
        if is_ajax:
            return JsonResponse({'success': False, 'message': message, 'errors': form.errors}, status=400)
        messages.error(request, message)
    return redirect('appeals:detail', pk=appeal.pk)


@require_POST
@login_required
def upload_document(request, pk):
    appeal = get_object_or_404(Appeal.objects.select_related('author', 'executor'), pk=pk)
    if not can_access_appeal(request.user, appeal):
        messages.error(request, 'Доступ запрещён.')
        return redirect('appeals:list')

    form = DocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.appeal = appeal
        doc.save()
        messages.success(request, 'Документ успешно прикреплён.')
    else:
        messages.error(request, 'Ошибка загрузки файла. Проверьте формат и размер.')
    return redirect('appeals:detail', pk=appeal.pk)


@login_required
def get_appeal_status_json(request, pk):
    appeal = get_object_or_404(Appeal.objects.select_related('status', 'author', 'executor'), pk=pk)

    if not can_access_appeal(request.user, appeal):
        return JsonResponse({'detail': 'Доступ запрещён.'}, status=403)

    return JsonResponse({
        'status': appeal.status.code,
        'status_name': appeal.status.name,
        'color': appeal.status.color,
        'allowed_next': appeal.get_allowed_transition_codes(request.user),
        'workflow_steps': appeal.workflow_steps,
        'is_terminal': appeal.status.code in Appeal.TERMINAL_STATUSES,
    })
