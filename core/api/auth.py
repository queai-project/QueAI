"""
Auth para /api/v1/.

Único esquema: bearer token comparado contra `settings.QUEAI_API_TOKEN`
con `hmac.compare_digest` para evitar timing attacks. La sesión Django
NO autoriza llamadas a la API (queremos un modelo de auth predecible
desde scripts y CI).
"""

from __future__ import annotations

import hmac
from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def _extract_token(request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def api_token_required(view):
    """Exige `Authorization: Bearer <QUEAI_API_TOKEN>`."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        expected = getattr(settings, "QUEAI_API_TOKEN", "") or ""
        provided = _extract_token(request)
        if not expected:
            return JsonResponse(
                {"error": "server_misconfigured", "detail": "QUEAI_API_TOKEN no configurado."},
                status=500,
            )
        if not provided:
            return JsonResponse(
                {"error": "unauthorized", "detail": "Falta header Authorization: Bearer <token>."},
                status=401,
            )
        if not hmac.compare_digest(provided, expected):
            return JsonResponse(
                {"error": "forbidden", "detail": "Token inválido."},
                status=403,
            )
        return view(request, *args, **kwargs)

    return wrapper
