from django.contrib.auth import get_user_model
from django.db import models


class AuditEvent(models.Model):
    """
    Registro inmutable de acciones del kernel.

    Una fila por acción mutante (install / start / stop / uninstall / delete /
    save_env / download). Se purga automáticamente cuando el total supera
    settings.QUEAI_AUDIT_MAX_EVENTS — ver core.audit.log() y core.audit.maybe_purge().
    """

    SOURCE_CHOICES = [
        ("ui", "UI"),
        ("api", "API"),
        ("cli", "CLI"),
        ("system", "System"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=60, db_index=True)
    target = models.CharField(max_length=200, blank=True, db_index=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="system", db_index=True)
    success = models.BooleanField(default=True, db_index=True)
    message = models.TextField(blank=True)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit event"
        verbose_name_plural = "Audit events"

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.source}:{self.action} on {self.target}"
