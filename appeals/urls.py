from django.urls import path
from . import views

app_name = 'appeals'

urlpatterns = [
    path('', views.appeal_list, name='list'),
    path('create/', views.appeal_create, name='create'),
    path('<int:pk>/', views.appeal_detail, name='detail'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
    path('<int:pk>/upload/', views.upload_document, name='upload_document'),
    path('<int:pk>/status-json/', views.get_appeal_status_json, name='status_json'),
]