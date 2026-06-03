from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from module_manager.models import AvailableApp


def home_view(request: HttpRequest):
    return render(request, "home.html")


def health_view(request: HttpRequest):
    """
    Endpoint público sin auth: usado por el healthcheck de Docker y por
    monitores externos. No revela información sensible.
    """
    try:
        plugins_count = AvailableApp.objects.count()
        db_ok = True
    except Exception:
        plugins_count = None
        db_ok = False

    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": settings.QUEAI_VERSION or "unknown",
        "debug": settings.DEBUG,
        "plugins": plugins_count,
    }
    return JsonResponse(payload, status=200 if db_ok else 503)
