
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from .views import home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('manager/', include('module_manager.urls')),
    path('marketplace/', include('marketplace.urls')),
    path('monitor/', include('system_monitor.urls')),
]

urlpatterns += staticfiles_urlpatterns()
