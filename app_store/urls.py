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
]