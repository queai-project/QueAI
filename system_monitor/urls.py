from . import views
from django.urls import path

urlpatterns = [
    path('', views.stats_dashboard, name='stats_dashboard'),
    path('stats/<str:folder_name>/', views.app_stats, name='app_stats'),
]