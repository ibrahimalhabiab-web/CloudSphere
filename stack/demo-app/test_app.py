#!/usr/bin/env python3
"""Tests for CloudSphere state changes, metrics, and presentation UI."""

import json
from http.server import ThreadingHTTPServer
import threading
import unittest
import urllib.request

import app


class DemoApplicationTests(unittest.TestCase):
    def setUp(self):
        app.reset_demo_state()

    def test_metric_label_escapes_prometheus_special_characters(self):
        self.assertEqual(app.metric_label('a"b\\c\n'), 'a\\"b\\\\c\\n')

    def test_reset_returns_business_counters_to_initial_values(self):
        with app.LOCK:
            app.STATE["orders_total"] = 4
            app.STATE["revenue_total"] = 99.5
            app.STATE["inventory_level"] = 12
            app.REQUESTS[("GET", "/simulate/order", "200")] = 4

        snapshot = app.reset_demo_state()

        self.assertEqual(snapshot, app.INITIAL_STATE)
        self.assertEqual(dict(app.REQUESTS), {})

    def test_metrics_include_required_business_series(self):
        metrics = app.render_metrics().decode("utf-8")
        for metric in (
            "demo_orders_total",
            "demo_revenue_total",
            "demo_inventory_level",
            "demo_application_errors_total",
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
        self.assertEqual(snapshot["service"]["name"], "CloudSphere Demo Control")

    def test_invalid_order_is_rejected_without_changing_state(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            app.create_order(0, 1)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            app.create_order(100, 101)
        self.assertEqual(app.STATE, app.INITIAL_STATE)

    def test_dashboard_contains_presentation_controls(self):
        page = app.DASHBOARD_HTML.decode("utf-8")
        for expected in (
            "CloudSphere Demo Control",
            "/assets/cloudsphere-avatar.png",
            "Generate 3 demo orders",
            "Trigger alert sequence",
            "Reset all metrics",
            "/simulate/error",
            "/api/state",
        ):
            self.assertIn(expected, page)


class DemoApplicationHTTPTests(unittest.TestCase):
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
        app.reset_demo_state()

    def test_root_serves_html_console(self):
        with urllib.request.urlopen(f"{self.base_url}/", timeout=2) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            self.assertIn("CloudSphere", body)

    def test_state_api_returns_json(self):
        with urllib.request.urlopen(f"{self.base_url}/api/state", timeout=2) as response:
            payload = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["state"]["inventory_level"], 100)
            self.assertEqual(payload["service"]["version"], "2.1.0")

    def test_brand_avatar_is_served_as_png(self):
        with urllib.request.urlopen(f"{self.base_url}{app.BRAND_AVATAR_URL}", timeout=2) as response:
            body = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertEqual(response.headers.get("Cache-Control"), "public, max-age=86400")
            self.assertTrue(body.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
