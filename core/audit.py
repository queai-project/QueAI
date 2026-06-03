"""
Audit log: helpers para registrar acciones del kernel y auto-purgar
cuando el log crece más allá de QUEAI_AUDIT_MAX_EVENTS.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _model():
    # Importación tardía para evitar carga del ORM durante el import del módulo.
    from .models import AuditEvent

    return AuditEvent


def log(
    *,
    action: str,
    target: str = "",
    source: str = "system",
    success: bool = True,
    message: str = "",
    user: Any = None,
) -> None:
    """Inserta un AuditEvent y dispara purge si toca."""
    try:
        _model().objects.create(
            action=action[:60],
            target=target[:200],
            source=source,
            success=success,
            message=message,
            user=user if (user and getattr(user, "is_authenticated", False)) else None,
        )
    except Exception as exc:
        # El audit no debe nunca romper el flow principal.
        logger.warning("audit log failed for %s: %s", action, exc)
        return
    maybe_purge()


def maybe_purge() -> int:
    """Si la tabla supera el techo, borra los más viejos hasta volver a KEEP."""
    max_events = getattr(settings, "QUEAI_AUDIT_MAX_EVENTS", 5000)
    keep = getattr(settings, "QUEAI_AUDIT_KEEP_AFTER_PURGE", 4000)
    AuditEvent = _model()

    total = AuditEvent.objects.count()
    if total <= max_events:
        return 0
    to_delete = total - keep
    # Borrado en bloque por PK para que sea barato (índice).
    victim_ids = list(
        AuditEvent.objects.order_by("timestamp").values_list("pk", flat=True)[:to_delete]
    )
    AuditEvent.objects.filter(pk__in=victim_ids).delete()
    logger.info("audit purge: removed %d old events (total was %d)", len(victim_ids), total)
    return len(victim_ids)


def record(action: str, source: str = "ui"):
    """
    Decorator para envolver una view. Loggea automáticamente success/failure
    leyendo `manifest_folder_name` del POST como target. Para casos
    complejos, llama a `audit.log(...)` directamente desde la view.
    """

    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            target = (
                kwargs.get("folder_name")
                or (request.POST.get("manifest_folder_name") if request.method == "POST" else "")
                or ""
            )
            try:
                response = view(request, *args, **kwargs)
            except Exception as exc:
                log(
                    action=action,
                    target=target,
                    source=source,
                    success=False,
                    message=str(exc)[:500],
                    user=getattr(request, "user", None),
                )
                raise
            status = getattr(response, "status_code", 200)
            log(
                action=action,
                target=target,
                source=source,
                success=200 <= status < 400,
                message=f"HTTP {status}",
                user=getattr(request, "user", None),
            )
            return response

        return wrapper

    return deco
