"""
Tests del API REST /api/v1/.

Cubren:
- Auth: token correcto / inválido / ausente.
- Health (público).
- Catálogo + lifecycle (mockeando subprocess).
- OpenAPI + Swagger UI accesibles.
"""

from __future__ import annotations

from unittest import mock

from django.test import Client, TestCase, override_settings

from module_manager.models import AvailableApp

API_TOKEN = "test-api-token-secret"


@override_settings(QUEAI_API_TOKEN=API_TOKEN)
class APIAuthTests(TestCase):
    def test_missing_token_returns_401(self):
        response = Client().get("/api/v1/plugins/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "unauthorized")

    def test_wrong_token_returns_403(self):
        response = Client().get(
            "/api/v1/plugins/",
            HTTP_AUTHORIZATION="Bearer not-the-token",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "forbidden")

    def test_valid_token_returns_200(self):
        response = Client().get(
            "/api/v1/plugins/",
            HTTP_AUTHORIZATION=f"Bearer {API_TOKEN}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)


class APIPublicEndpointsTests(TestCase):
    """Health, openapi.json y /docs no requieren token."""

    def test_health_is_public(self):
        response = Client().get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_openapi_schema_is_public(self):
        response = Client().get("/api/v1/openapi.json")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["openapi"], "3.0.3")
        self.assertIn("/plugins/", body["paths"])
        self.assertIn("bearerAuth", body["components"]["securitySchemes"])


@override_settings(QUEAI_API_TOKEN=API_TOKEN)
class APILifecycleTests(TestCase):
    def setUp(self):
        AvailableApp.objects.create(
            name="demo",
            folder_name="QueAI-Demo-MS",
            display_name="Demo",
            logo="logo.png",
            ui_entry_point="",
            configuration_entry_point="",
            documentation_entry_point="",
            version="1.0.0",
            description="",
            author="",
            lic="MIT",
            is_installed=False,
        )
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {API_TOKEN}"}

    def test_plugins_list_returns_demo(self):
        with mock.patch("core.api.views._is_app_running_cached", return_value=False):
            response = Client().get("/api/v1/plugins/", **self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["plugins"][0]["folder_name"], "QueAI-Demo-MS")

    def test_plugin_detail_404_when_unknown(self):
        response = Client().get("/api/v1/plugins/nope/", **self.headers)
        self.assertEqual(response.status_code, 404)

    @mock.patch("core.api.views.subprocess.run")
    def test_install_calls_compose_up(self, run_mock):
        run_mock.return_value = mock.Mock(returncode=0)
        response = Client().post("/api/v1/plugins/QueAI-Demo-MS/install", **self.headers)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "installed")
        invoked_cmd = run_mock.call_args.args[0]
        self.assertIn("up", invoked_cmd)
        self.assertIn("--build", invoked_cmd)

    @mock.patch("core.api.views.subprocess.run")
    def test_stop_calls_compose_stop(self, run_mock):
        run_mock.return_value = mock.Mock(returncode=0)
        response = Client().post("/api/v1/plugins/QueAI-Demo-MS/stop", **self.headers)
        self.assertEqual(response.status_code, 200)
        invoked_cmd = run_mock.call_args.args[0]
        self.assertIn("stop", invoked_cmd)
