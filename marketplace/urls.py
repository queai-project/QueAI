from . import views
from django.urls import path

urlpatterns = [
    path('', views.marketplace, name='marketplace'),
    path('download/', views.download_plugin, name='download_plugin'),
]