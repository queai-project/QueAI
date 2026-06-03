from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from .views import (
    account_view,
    audit_view,
    backup_view,
    health_view,
    home_view,
    welcome_dismiss,
    welcome_view,
)

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
    path("account/", account_view, name="account"),
    path("welcome/", welcome_view, name="welcome"),
    path("welcome/dismiss/", welcome_dismiss, name="welcome_dismiss"),
    path("audit/", audit_view, name="audit"),
    path("backup", backup_view, name="backup"),
    path("admin/", admin.site.urls),
    path("manager/", include("module_manager.urls")),
    path("marketplace/", include("marketplace.urls")),
    path("monitor/", include("system_monitor.urls")),
    path("api/v1/", include("core.api.urls")),
]

urlpatterns += staticfiles_urlpatterns()
