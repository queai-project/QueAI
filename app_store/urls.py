from . import views
from django.urls import path

urlpatterns = [
    path('', views.get_apps, name='get_apps'),
    path('install/', views.install_app, name='install_app'),
    path('start/', views.start_app, name='start_app'),
    path('stop/', views.stop_app, name='stop_app'),
    path('uninstall/', views.uninstall_app, name='uninstall_app'),
    path('logo/<str:plugin_name>/<str:filename>', views.plugin_logo, name='plugin_logo'),
    path('logs/<str:folder_name>/', views.app_logs, name='app_logs'),
    # Nuevas rutas para .env
    path('get_env/<str:folder_name>/', views.get_env_config, name='get_env_config'),
    path('save_env/', views.save_env_config, name='save_env_config'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('download/', views.download_plugin, name='download_plugin'),
    path('stats/<str:folder_name>/', views.app_stats, name='app_stats'),
    path('dashboard/', views.stats_dashboard, name='stats_dashboard'),
]