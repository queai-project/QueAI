
from django.contrib import admin
from django.urls import path, include
from .views import home_view

urlpatterns = [

    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('store/', include('app_store.urls')),
]
