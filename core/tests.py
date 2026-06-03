"""
Smoke tests del kernel.

Cubren:
- /health responde y no requiere auth.
- Rutas protegidas redirigen a /login si no hay sesión.
- ensure_admin crea / no crea según las variables de entorno.
"""

import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase


class HealthEndpointTests(TestCase):
    def test_health_returns_ok_without_auth(self):
        response = Client().get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("version", body)
        self.assertIn("plugins", body)


class AuthRequiredTests(TestCase):
    """Las rutas operativas exigen sesión iniciada."""

    PROTECTED = ["/manager/", "/marketplace/", "/monitor/"]

    def test_protected_routes_redirect_to_login(self):
        client = Client()
        for path in self.PROTECTED:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response["Location"])

    def test_login_form_renders(self):
        response = Client().get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar")


class EnsureAdminCommandTests(TestCase):
    User = get_user_model()

    def test_no_user_var_does_nothing(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in ("QUEAI_ADMIN_USER", "QUEAI_ADMIN_PASSWORD"):
                os.environ.pop(key, None)
            call_command("ensure_admin")
        self.assertEqual(self.User.objects.count(), 0)

    def test_creates_superuser_from_env(self):
        with mock.patch.dict(
            os.environ,
            {
                "QUEAI_ADMIN_USER": "alice",
                "QUEAI_ADMIN_PASSWORD": "s3cret-pass",
                "QUEAI_ADMIN_EMAIL": "alice@example.com",
            },
        ):
            call_command("ensure_admin")
        user = self.User.objects.get(username="alice")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("s3cret-pass"))

    def test_existing_user_password_not_rotated_by_default(self):
        self.User.objects.create_user(
            username="bob", password="original", is_superuser=True, is_staff=True
        )
        with mock.patch.dict(
            os.environ,
            {
                "QUEAI_ADMIN_USER": "bob",
                "QUEAI_ADMIN_PASSWORD": "newpass",
            },
        ):
            call_command("ensure_admin")
        bob = self.User.objects.get(username="bob")
        self.assertTrue(bob.check_password("original"))

    def test_rotate_flag_updates_password(self):
        self.User.objects.create_user(
            username="carol", password="old", is_superuser=True, is_staff=True
        )
        with mock.patch.dict(
            os.environ,
            {
                "QUEAI_ADMIN_USER": "carol",
                "QUEAI_ADMIN_PASSWORD": "rotated",
                "QUEAI_ADMIN_ROTATE_PASSWORD": "true",
            },
        ):
            call_command("ensure_admin")
        carol = self.User.objects.get(username="carol")
        self.assertTrue(carol.check_password("rotated"))
