from django.urls import path

from . import views

urlpatterns = [
    path('', views.marketplace, name='marketplace'),
    path('download/', views.download_plugin, name='download_plugin'),
]
