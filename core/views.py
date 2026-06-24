from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from appeals.models import Appeal
from .forms import ProfileUpdateForm, UserRegistrationForm


def register_view(request):
    """Регистрация нового пользователя (только роль 'citizen')"""
    if request.user.is_authenticated:
        return redirect('appeals:list')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Автоматический вход после регистрации
            messages.success(request, f'Добро пожаловать, {user.first_name or user.username}!')
            return redirect('appeals:list')
    else:
        form = UserRegistrationForm()

    return render(request, 'core/register.html', {'form': form})


@login_required
def profile_view(request):
    """Просмотр и редактирование профиля"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('core:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    # Показываем статистику только для граждан
    my_appeals_count = Appeal.objects.filter(author=request.user).count() if request.user.role == 'citizen' else None

    return render(request, 'core/profile.html', {
        'form': form,
        'user': request.user,
        'my_appeals_count': my_appeals_count
    })


@login_required
def change_password(request):
    """Безопасное изменение пароля"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Важно: не разлогинивает пользователя
            messages.success(request, 'Пароль успешно изменён.')
            return redirect('core:profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'core/change_password.html', {'form': form})