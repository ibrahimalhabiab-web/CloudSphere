#!/usr/bin/env python3
"""Tests for CloudSphere state changes, metrics, and presentation UI."""

import json
from http.server import ThreadingHTTPServer
import os
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.request

import app


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None and timeout is not None:
            raise TimeoutError
        return self.returncode or 0


class CloudSphereApplicationTests(unittest.TestCase):
    def setUp(self):
        app.reset_cloudsphere_state()

    def test_metric_label_escapes_prometheus_special_characters(self):
        self.assertEqual(app.metric_label('a"b\\c\n'), 'a\\"b\\\\c\\n')

    def test_reset_returns_business_counters_to_initial_values(self):
        with app.LOCK:
            app.STATE["orders_total"] = 4
            app.STATE["revenue_total"] = 99.5
            app.STATE["inventory_level"] = 12
            app.REQUESTS[("GET", "/simulate/order", "200")] = 4

        snapshot = app.reset_cloudsphere_state()

        self.assertEqual(snapshot, app.INITIAL_STATE)
        self.assertEqual(dict(app.REQUESTS), {})

    def test_metrics_include_required_business_series(self):
        metrics = app.render_metrics().decode("utf-8")
        for metric in (
            "cloudsphere_orders_total",
            "cloudsphere_revenue_total",
            "cloudsphere_inventory_level",
            "cloudsphere_application_errors_total",
            "cloudsphere_cpu_stress_active",
            "cloudsphere_cpu_stress_remaining_seconds",
            "cloudsphere_cpu_stress_runs_total",
        ):
            self.assertIn(metric, metrics)

    def test_order_restock_and_error_actions_change_the_shared_state(self):
        state = app.create_order("125.50", "2")
        self.assertEqual(state["orders_total"], 1)
        self.assertEqual(state["revenue_total"], 125.5)
        self.assertEqual(state["inventory_level"], 98)

        self.assertEqual(app.restock_inventory("2"), 100)
        self.assertEqual(app.simulate_application_error(), 1)

        snapshot = app.state_snapshot()
        self.assertEqual(snapshot["state"]["application_errors_total"], 1)
        self.assertEqual(snapshot["service"]["name"], "CloudSphere Operations Console")

    def test_invalid_order_is_rejected_without_changing_state(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            app.create_order(0, 1)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            app.create_order(100, 101)
        self.assertEqual(app.STATE, app.INITIAL_STATE)

    def test_dashboard_contains_presentation_controls(self):
        page = app.DASHBOARD_HTML.decode("utf-8")
        for expected in (
            "CloudSphere Operations Console",
            "/assets/cloudsphere-avatar.png",
            "Generate 3 orders",
            "Trigger alert sequence",
            "Reset all metrics",
            "Infrastructure pulse",
            "Run 30-second server load",
            "/simulate/load/start",
            "/simulate/error",
            "/api/state",
        ):
            self.assertIn(expected, page)

    def test_public_page_is_read_only_and_excludes_private_operator_features(self):
        page = app.PUBLIC_HTML.decode("utf-8")

        self.assertIn("CloudSphere | Platform Status", page)
        self.assertIn("/assets/cloudsphere-avatar.png", page)
        self.assertIn("/api/public/status", page)
        self.assertNotIn("<button", page.lower())
        for forbidden in (
            "/simulate/",
            "/api/state",
            "grafana",
            "prometheus",
            "alertmanager",
            "create order",
            "generate 3 orders",
            "trigger alert",
            "reset all metrics",
            "restock",
            "cpu",
            "infrastructure pulse",
        ):
            self.assertNotIn(forbidden, page.lower())

    def test_public_status_snapshot_exposes_only_minimal_health_data(self):
        payload = app.public_status_snapshot()

        self.assertEqual(
            set(payload),
            {"service", "status", "uptime_seconds", "checked_at"},
        )
        self.assertEqual(payload["service"], "CloudSphere")
        self.assertEqual(payload["status"], "operational")
        self.assertGreaterEqual(payload["uptime_seconds"], 0)

    def test_controlled_cpu_load_is_single_run_and_stoppable(self):
        process = FakeProcess()
        with (
            mock.patch.object(app, "_launch_cpu_stress_worker", return_value=process),
            mock.patch.object(app, "_start_cpu_stress_watcher"),
        ):
            stress = app.start_controlled_cpu_load()
            self.assertTrue(stress["active"])
            self.assertEqual(stress["duration_seconds"], 30)
            self.assertEqual(stress["workers"], 1)
            with self.assertRaises(app.StressAlreadyRunningError):
                app.start_controlled_cpu_load()

            stopped = app.stop_controlled_cpu_load()
            self.assertFalse(stopped["active"])
            self.assertTrue(process.terminated)

    def test_reset_stops_an_active_cpu_load(self):
        process = FakeProcess()
        with (
            mock.patch.object(app, "_launch_cpu_stress_worker", return_value=process),
            mock.patch.object(app, "_start_cpu_stress_watcher"),
        ):
            app.start_controlled_cpu_load()
            snapshot = app.reset_cloudsphere_state()
        self.assertTrue(process.terminated)
        self.assertEqual(snapshot, app.INITIAL_STATE)


class CloudSphereApplicationHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        app.reset_cloudsphere_state()

    def test_root_serves_html_console(self):
        with urllib.request.urlopen(f"{self.base_url}/", timeout=2) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            self.assertIn("CloudSphere", body)

    def test_public_route_is_read_only_and_does_not_change_business_state(self):
        before = dict(app.STATE)

        with urllib.request.urlopen(f"{self.base_url}/public", timeout=2) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            self.assertIn("CloudSphere | Platform Status", body)

        self.assertEqual(app.STATE, before)

    def test_public_status_endpoint_returns_minimal_non_sensitive_json(self):
        before = dict(app.STATE)

        with urllib.request.urlopen(f"{self.base_url}/api/public/status", timeout=2) as response:
            payload = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertEqual(
                set(payload),
                {"service", "status", "uptime_seconds", "checked_at"},
            )
            self.assertEqual(payload["status"], "operational")

        self.assertEqual(app.STATE, before)

    def test_public_only_mode_allows_public_get_and_head_routes(self):
        allowed = (
            "/public",
            "/public/",
            "/api/public/status",
            "/assets/cloudsphere-avatar.png",
            "/health",
        )

        with mock.patch.dict(os.environ, {"PUBLIC_ONLY": "true"}):
            for path in allowed:
                with self.subTest(method="GET", path=path):
                    with urllib.request.urlopen(f"{self.base_url}{path}", timeout=2) as response:
                        self.assertEqual(response.status, 200)

                with self.subTest(method="HEAD", path=path):
                    request = urllib.request.Request(f"{self.base_url}{path}", method="HEAD")
                    with urllib.request.urlopen(request, timeout=2) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read(), b"")

    def test_public_only_status_does_not_parse_untrusted_query_parameters(self):
        with (
            mock.patch.dict(os.environ, {"PUBLIC_ONLY": "true"}),
            mock.patch.object(app, "parse_qs", side_effect=AssertionError("query parsed")),
        ):
            with urllib.request.urlopen(
                f"{self.base_url}/api/public/status?ignored=1",
                timeout=2,
            ) as response:
                self.assertEqual(response.status, 200)

    def test_public_only_mode_blocks_every_private_get_without_changing_state(self):
        private_gets = (
            "/",
            "/api/state",
            "/metrics",
            "/simulate/order?amount=125&quantity=2",
            "/simulate/restock?quantity=50",
            "/simulate/error",
            "/alerts",
        )
        before = dict(app.STATE)

        with mock.patch.dict(os.environ, {"PUBLIC_ONLY": "true"}):
            for path in private_gets:
                with self.subTest(path=path):
                    with self.assertRaises(urllib.error.HTTPError) as raised:
                        urllib.request.urlopen(f"{self.base_url}{path}", timeout=2)
                    self.assertEqual(raised.exception.code, 404)

        self.assertEqual(app.STATE, before)

    def test_public_only_mode_blocks_every_post_without_changing_state(self):
        private_posts = (
            ("/simulate/reset", None, {}),
            ("/simulate/load/start", None, {"X-CloudSphere-Control": "1"}),
            ("/simulate/load/stop", None, {"X-CloudSphere-Control": "1"}),
            ("/alerts", b'{"alerts":[{"status":"firing"}]}', {"Content-Type": "application/json"}),
            ("/public", None, {}),
        )
        before = dict(app.STATE)

        with mock.patch.dict(os.environ, {"PUBLIC_ONLY": "true"}):
            for path, body, headers in private_posts:
                with self.subTest(path=path):
                    request = urllib.request.Request(
                        f"{self.base_url}{path}",
                        data=body,
                        headers=headers,
                        method="POST",
                    )
                    with self.assertRaises(urllib.error.HTTPError) as raised:
                        urllib.request.urlopen(request, timeout=2)
                    self.assertEqual(raised.exception.code, 404)

        self.assertEqual(app.STATE, before)

    def test_public_only_mode_blocks_head_for_private_route(self):
        before = dict(app.STATE)
        request = urllib.request.Request(f"{self.base_url}/metrics", method="HEAD")

        with mock.patch.dict(os.environ, {"PUBLIC_ONLY": "true"}):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=2)

        self.assertEqual(raised.exception.code, 404)
        self.assertEqual(app.STATE, before)

    def test_default_mode_keeps_private_operator_endpoint_behavior(self):
        with mock.patch.dict(os.environ, {"PUBLIC_ONLY": ""}):
            with urllib.request.urlopen(
                f"{self.base_url}/simulate/order?amount=125&quantity=2",
                timeout=2,
            ) as response:
                payload = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["accepted"])
        self.assertEqual(app.STATE["orders_total"], 1)
        self.assertEqual(app.STATE["inventory_level"], 98)

    def test_state_api_returns_json(self):
        with urllib.request.urlopen(f"{self.base_url}/api/state", timeout=2) as response:
            payload = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["state"]["inventory_level"], 100)
            self.assertEqual(payload["service"]["version"], "2.3.0")
            self.assertFalse(payload["stress"]["active"])
            self.assertEqual(payload["stress"]["duration_seconds"], 30)

    def test_load_endpoint_requires_control_header(self):
        request = urllib.request.Request(f"{self.base_url}/simulate/load/start", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(raised.exception.code, 403)

    def test_brand_avatar_is_served_as_png(self):
        with urllib.request.urlopen(f"{self.base_url}{app.BRAND_AVATAR_URL}", timeout=2) as response:
            body = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertEqual(response.headers.get("Cache-Control"), "public, max-age=86400")
            self.assertTrue(body.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
