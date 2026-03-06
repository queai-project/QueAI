
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from .views import home_view

urlpatterns = [

    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('store/', include('app_store.urls')),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
