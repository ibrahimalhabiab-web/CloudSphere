#!/usr/bin/env python3
"""Unit tests for deterministic metric formatting and demonstration reset behavior."""

import unittest

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


if __name__ == "__main__":
    unittest.main()
