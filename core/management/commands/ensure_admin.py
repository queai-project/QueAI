"""
Crea (o actualiza) el superuser inicial de QueAI a partir de variables de
entorno. Idempotente: corre seguro en cada arranque del contenedor.

Variables:
  QUEAI_ADMIN_USER       — nombre de usuario. Si está vacío, el comando
                            no hace nada y muestra una nota.
  QUEAI_ADMIN_PASSWORD   — password en texto plano. Obligatorio si se
                            define QUEAI_ADMIN_USER.
  QUEAI_ADMIN_EMAIL      — email opcional. Default: admin@queai.local.

Comportamiento:
  - Si el user no existe → lo crea como superuser.
  - Si existe → actualiza el password sólo cuando ROTATE=true; si no,
    solo lo deja con is_superuser/is_staff = True.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Asegura que exista el superuser inicial a partir de variables de entorno."

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = (os.getenv("QUEAI_ADMIN_USER") or "").strip()
        password = os.getenv("QUEAI_ADMIN_PASSWORD") or ""
        email = (os.getenv("QUEAI_ADMIN_EMAIL") or "admin@queai.local").strip()
        rotate = (os.getenv("QUEAI_ADMIN_ROTATE_PASSWORD") or "").lower() in {
            "1",
            "true",
            "yes",
        }

        if not username:
            self.stdout.write(
                "QUEAI_ADMIN_USER no está definido; saltando creación automática "
                "de admin. Crea uno manualmente con `python manage.py createsuperuser`."
            )
            return

        if not password:
            self.stderr.write(
                f"QUEAI_ADMIN_USER='{username}' pero QUEAI_ADMIN_PASSWORD está vacío. "
                "Defínelo o crea el admin manualmente."
            )
            return

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        user.is_staff = True
        user.is_superuser = True
        user.email = email or user.email

        if created or rotate:
            user.set_password(password)
            user.save()
            action = "Creado" if created else "Password rotada para"
            self.stdout.write(self.style.SUCCESS(f"{action} admin '{username}'."))
        else:
            user.save()
            self.stdout.write(
                f"Admin '{username}' ya existía (password no rotada). "
                "Define QUEAI_ADMIN_ROTATE_PASSWORD=true para forzar."
            )
