"""
Variables disponibles en todos los templates (vía base.html).

Inyectado en TEMPLATES.OPTIONS.context_processors.
"""

from django.conf import settings


def queai(request):
    return {
        "queai_version": getattr(settings, "QUEAI_VERSION", "") or "",
    }
