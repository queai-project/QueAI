"""
Smoke tests del flujo de ciclo de vida de plugins.

Mockean `subprocess.run` para no requerir Docker durante los tests.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from module_manager.models import AvailableApp


def _make_plugin_dir(tmp_path: Path, folder: str, manifest_name: str):
    plugin = tmp_path / folder
    plugin.mkdir(parents=True, exist_ok=True)
    (plugin / "manifest.json").write_text(
        json.dumps(
            {
                "name": manifest_name,
                "display_name": manifest_name.upper(),
                "version": "1.0.0",
                "ui_entry_point": f"/api/{manifest_name}/ui",
            }
        )
    )
    (plugin / "docker-compose.yml").write_text("services:\n  api:\n    image: alpine\n")
    return plugin


class CatalogScanTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="op", password="op", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.force_login(user)
        # El wizard de onboarding redirige cuando no hay plugins; aquí
        # queremos probar la vista del catálogo directamente.
        session = self.client.session
        session["welcome_dismissed"] = True
        session.save()

    def test_get_apps_discovers_valid_plugin(self):
        with TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp)
            _make_plugin_dir(plugin_dir, "QueAI-Demo-MS", "demo_plugin")

            with override_settings(PLUGINS_DIR=plugin_dir), mock.patch(
                "module_manager.views._is_app_running_cached", return_value=False
            ):
                response = self.client.get("/manager/")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                AvailableApp.objects.filter(name="demo_plugin").exists()
            )


class LifecycleActionsTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="op", password="op", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.force_login(user)
        self.app = AvailableApp.objects.create(
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

    @mock.patch("module_manager.views.subprocess.run")
    def test_install_invokes_compose_up(self, run_mock):
        run_mock.return_value = mock.Mock(returncode=0)
        response = self.client.post(
            "/manager/install/", {"manifest_folder_name": "QueAI-Demo-MS"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(run_mock.called)
        invoked_cmd = run_mock.call_args.args[0]
        self.assertIn("up", invoked_cmd)
        self.assertIn("--build", invoked_cmd)
        self.app.refresh_from_db()
        self.assertTrue(self.app.is_installed)

    @mock.patch("module_manager.views.subprocess.run")
    def test_stop_invokes_compose_stop(self, run_mock):
        run_mock.return_value = mock.Mock(returncode=0)
        self.client.post(
            "/manager/stop/", {"manifest_folder_name": "QueAI-Demo-MS"}
        )
        invoked_cmd = run_mock.call_args.args[0]
        self.assertIn("stop", invoked_cmd)


class WelcomeOnboardingTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="op", password="op", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.force_login(user)

    def test_get_apps_redirects_to_welcome_when_empty(self):
        # Sin plugins en BD y sin descartar el wizard → redirect a /welcome/.
        response = self.client.get("/manager/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/welcome", response["Location"])

    def test_dismiss_sets_session_flag_and_redirects(self):
        response = self.client.post("/welcome/dismiss/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/manager", response["Location"])
        # Y ya no debe redirigir al wizard.
        response2 = self.client.get("/manager/")
        self.assertEqual(response2.status_code, 200)


class RefreshEndpointTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="op", password="op", is_staff=True, is_superuser=True
        )
        self.client = Client()
        self.client.force_login(user)

    @mock.patch("module_manager.views._invalidate_running_cache")
    def test_refresh_invalidates_cache_and_redirects(self, invalidate):
        response = self.client.post("/manager/refresh/")
        self.assertEqual(response.status_code, 302)
        invalidate.assert_called_once_with()
