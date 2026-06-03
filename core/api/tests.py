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

    def test_plugin_detail_accepts_slug_name(self):
        """El usuario puede pasar el slug corto (name) además del folder largo."""
        with mock.patch("core.api.views._is_app_running_cached", return_value=False):
            response = Client().get("/api/v1/plugins/demo/", **self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        # Devuelve el folder real, no lo que mandó el cliente.
        self.assertEqual(body["folder_name"], "QueAI-Demo-MS")

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


@override_settings(QUEAI_API_TOKEN=API_TOKEN, QUEAI_AUDIT_MAX_EVENTS=20, QUEAI_AUDIT_KEEP_AFTER_PURGE=10)
class APIAuditTests(TestCase):
    def setUp(self):
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {API_TOKEN}"}

    def test_audit_log_records_via_decorator(self):
        AvailableApp.objects.create(
            name="demo",
            folder_name="QueAI-Demo-MS",
            display_name="Demo",
            logo="",
            ui_entry_point="",
            configuration_entry_point="",
            documentation_entry_point="",
            version="1.0.0",
            description="",
            author="",
            lic="MIT",
            is_installed=True,
        )
        from core.models import AuditEvent

        with mock.patch("core.api.views.subprocess.run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=0)
            Client().post("/api/v1/plugins/QueAI-Demo-MS/stop", **self.headers)
        events = AuditEvent.objects.filter(action="stop")
        self.assertEqual(events.count(), 1)
        ev = events.first()
        self.assertEqual(ev.source, "api")
        self.assertEqual(ev.target, "QueAI-Demo-MS")
        self.assertTrue(ev.success)

    def test_audit_auto_purge_drops_oldest(self):
        from core import audit as audit_module
        from core.models import AuditEvent

        for i in range(25):
            audit_module.log(action="ping", target=f"t{i}", source="system")
        # max=20, keep=10 → al pasar 20, debe quedar a 10.
        self.assertLessEqual(AuditEvent.objects.count(), 20)
        # El más viejo de los conservados no debe ser t0.
        oldest = AuditEvent.objects.order_by("timestamp").first()
        self.assertNotEqual(oldest.target, "t0")

    def test_audit_list_endpoint_filters(self):
        from core import audit as audit_module

        audit_module.log(action="start", target="foo", source="cli")
        audit_module.log(action="stop", target="foo", source="cli")
        audit_module.log(action="start", target="bar", source="ui")

        response = Client().get("/api/v1/audit/?action=start", **self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertTrue(all(e["action"] == "start" for e in body["events"]))


@override_settings(QUEAI_API_TOKEN=API_TOKEN)
class APIBackupTests(TestCase):
    def setUp(self):
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {API_TOKEN}"}

    def test_backup_returns_tar_with_metadata(self):
        import io
        import json
        import tarfile

        response = Client().get("/api/v1/backup", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/gzip")
        self.assertIn("attachment", response["Content-Disposition"])
        # El payload debe ser un tar.gz válido con metadata.json.
        buf = io.BytesIO(b"".join(response.streaming_content) if response.streaming else response.content)
        with tarfile.open(fileobj=buf, mode="r:gz") as t:
            names = t.getnames()
            self.assertIn("metadata.json", names)
            meta = json.loads(t.extractfile("metadata.json").read())
        self.assertEqual(meta["kind"], "queai-backup-light")


@override_settings(QUEAI_API_TOKEN=API_TOKEN)
class APIHealthcheckTests(TestCase):
    def setUp(self):
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {API_TOKEN}"}
        AvailableApp.objects.create(
            name="hc_demo",
            folder_name="QueAI-Hc-MS",
            display_name="Hc",
            logo="", ui_entry_point="", configuration_entry_point="",
            documentation_entry_point="", version="1.0.0", description="",
            author="", lic="MIT", is_installed=True,
        )

    def test_no_endpoint_returns_null(self):
        with mock.patch("core.api.views._load_manifest", return_value={}):
            response = Client().get("/api/v1/plugins/QueAI-Hc-MS/healthcheck", **self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["healthy"])
        self.assertEqual(body["error"], "no_healthcheck_endpoint")

    @mock.patch("core.healthcheck.requests.get")
    def test_healthy_when_endpoint_returns_200(self, get_mock):
        from core import healthcheck as hc_mod

        hc_mod.invalidate()  # limpia cache entre tests
        get_mock.return_value = mock.Mock(status_code=200)
        manifest = {"healthcheck_entry_point": "/api/demo/health"}
        with mock.patch("core.api.views._load_manifest", return_value=manifest), \
             mock.patch("core.api.views._is_app_running_cached", return_value=True):
            response = Client().get("/api/v1/plugins/QueAI-Hc-MS/healthcheck", **self.headers)
        body = response.json()
        self.assertTrue(body["healthy"])
        self.assertEqual(body["status_code"], 200)
