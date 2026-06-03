"""
Rutas REST montadas en /api/v1/.
"""

from django.urls import path

from . import views

urlpatterns = [
    # Meta + docs
    path("health", views.health, name="api_health"),
    path("openapi.json", views.openapi_schema, name="api_openapi"),
    path("docs", views.docs_ui, name="api_docs"),

    # Catálogo
    path("plugins/", views.plugins_list, name="api_plugins_list"),
    path("plugins/<str:folder_name>/", views.plugin_detail, name="api_plugin_detail"),

    # Lifecycle
    path("plugins/<str:folder_name>/install", views.plugin_install, name="api_plugin_install"),
    path("plugins/<str:folder_name>/start", views.plugin_start, name="api_plugin_start"),
    path("plugins/<str:folder_name>/stop", views.plugin_stop, name="api_plugin_stop"),
    path("plugins/<str:folder_name>/uninstall", views.plugin_uninstall, name="api_plugin_uninstall"),
    path("plugins/<str:folder_name>/delete", views.plugin_delete, name="api_plugin_delete"),

    # Logs / stats
    path("plugins/<str:folder_name>/logs", views.plugin_logs, name="api_plugin_logs"),
    path("plugins/<str:folder_name>/stats", views.plugin_stats, name="api_plugin_stats"),

    # .env
    path("plugins/<str:folder_name>/env", views.plugin_env, name="api_plugin_env"),

    # Marketplace
    path("marketplace/", views.marketplace_list, name="api_marketplace_list"),
    path("marketplace/download", views.marketplace_download, name="api_marketplace_download"),
]
