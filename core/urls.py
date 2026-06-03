from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from .views import health_view, home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("health", health_view, name="health"),
    path("health/", health_view),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("manager/", include("module_manager.urls")),
    path("marketplace/", include("marketplace.urls")),
    path("monitor/", include("system_monitor.urls")),
]

urlpatterns += staticfiles_urlpatterns()
