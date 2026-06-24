from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Аутентификация и регистрация
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        extra_context={'title': 'Вход в систему'}
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='appeals:list'), name='logout'),
    path('accounts/', include('core.urls', namespace='core')),

    # Приложения проекта
    path('', include('appeals.urls', namespace='appeals')),
    path('reports/', include('reports.urls', namespace='reports')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Настройка заголовков для отладки
    admin.site.site_header = 'Администрирование ИС "Электронная приемная"'
    admin.site.site_title = 'Электронная приемная'
    admin.site.index_title = 'Панель управления'