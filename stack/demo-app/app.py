#!/usr/bin/env python3
"""Dependency-free demonstration service with Prometheus business metrics."""

from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
from urllib.parse import parse_qs, urlparse


START_TIME = time.time()
LOCK = threading.Lock()
INITIAL_STATE = {
    "orders_total": 0,
    "revenue_total": 0.0,
    "inventory_level": 100,
    "application_errors_total": 0,
    "alert_notifications_total": 0,
}
STATE = dict(INITIAL_STATE)
REQUESTS = defaultdict(int)


def json_bytes(payload):
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def metric_label(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def reset_demo_state():
    """Return the in-memory demonstration counters to their initial values."""
    with LOCK:
        STATE.clear()
        STATE.update(INITIAL_STATE)
        REQUESTS.clear()
        return dict(STATE)


def render_metrics():
    with LOCK:
        snapshot = dict(STATE)
        requests = dict(REQUESTS)

    lines = [
        "# HELP demo_app_info Static information about the demonstration application.",
        "# TYPE demo_app_info gauge",
        'demo_app_info{service="order-demo",version="1.0.0"} 1',
        "# HELP demo_app_uptime_seconds Seconds since the application started.",
        "# TYPE demo_app_uptime_seconds gauge",
        f"demo_app_uptime_seconds {time.time() - START_TIME:.3f}",
        "# HELP demo_orders_total Total simulated orders accepted.",
        "# TYPE demo_orders_total counter",
        f"demo_orders_total {snapshot['orders_total']}",
        "# HELP demo_revenue_total Total simulated order revenue.",
        "# TYPE demo_revenue_total counter",
        f"demo_revenue_total {snapshot['revenue_total']:.2f}",
        "# HELP demo_inventory_level Current simulated inventory units.",
        "# TYPE demo_inventory_level gauge",
        f"demo_inventory_level {snapshot['inventory_level']}",
        "# HELP demo_application_errors_total Total simulated application errors.",
        "# TYPE demo_application_errors_total counter",
        f"demo_application_errors_total {snapshot['application_errors_total']}",
        "# HELP demo_alert_notifications_total Alerts delivered to the demonstration webhook.",
        "# TYPE demo_alert_notifications_total counter",
        f"demo_alert_notifications_total {snapshot['alert_notifications_total']}",
        "# HELP demo_http_requests_total HTTP requests processed by path and status.",
        "# TYPE demo_http_requests_total counter",
    ]
    for (method, path, status), value in sorted(requests.items()):
        labels = f'method="{metric_label(method)}",path="{metric_label(path)}",status="{metric_label(status)}"'
        lines.append(f"demo_http_requests_total{{{labels}}} {value}")
    return ("\n".join(lines) + "\n").encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "MonitoringDemo/1.0"

    def log_message(self, fmt, *args):
        print(json.dumps({"time": time.time(), "client": self.client_address[0], "message": fmt % args}), flush=True)

    def record(self, status):
        path = urlparse(self.path).path
        with LOCK:
            REQUESTS[(self.command, path, str(status))] += 1

    def send_payload(self, status, payload, content_type="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        self.record(status)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/health":
            self.send_payload(200, {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 3)})
            return

        if parsed.path == "/metrics":
            self.send_payload(200, render_metrics(), "text/plain; version=0.0.4; charset=utf-8")
            return

        if parsed.path == "/simulate/order":
            try:
                amount = float(query.get("amount", ["100"])[0])
                quantity = int(query.get("quantity", ["1"])[0])
                if amount <= 0 or quantity <= 0:
                    raise ValueError("amount and quantity must be positive")
                with LOCK:
                    if quantity > STATE["inventory_level"]:
                        raise ValueError("insufficient simulated inventory")
                    STATE["orders_total"] += 1
                    STATE["revenue_total"] += amount
                    STATE["inventory_level"] -= quantity
                    snapshot = dict(STATE)
                self.send_payload(200, {"accepted": True, "amount": amount, "quantity": quantity, "state": snapshot})
            except (TypeError, ValueError) as exc:
                self.send_payload(400, {"accepted": False, "error": str(exc)})
            return

        if parsed.path == "/simulate/restock":
            try:
                quantity = int(query.get("quantity", ["50"])[0])
                if quantity <= 0:
                    raise ValueError("quantity must be positive")
                with LOCK:
                    STATE["inventory_level"] += quantity
                    level = STATE["inventory_level"]
                self.send_payload(200, {"restocked": quantity, "inventory_level": level})
            except (TypeError, ValueError) as exc:
                self.send_payload(400, {"error": str(exc)})
            return

        if parsed.path == "/simulate/error":
            with LOCK:
                STATE["application_errors_total"] += 1
            self.send_payload(500, {"status": "simulated failure"})
            return

        if parsed.path == "/":
            self.send_payload(
                200,
                {
                    "service": "order-demo",
                    "purpose": "Generate application and business metrics for the monitoring platform.",
                    "endpoints": [
                        "/health",
                        "/metrics",
                        "/simulate/order?amount=125&quantity=1",
                        "/simulate/restock?quantity=50",
                        "/simulate/error",
                        "POST /simulate/reset",
                    ],
                },
            )
            return

        self.send_payload(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/simulate/reset":
            self.send_payload(200, {"reset": True, "state": reset_demo_state()})
            return

        if path != "/alerts":
            self.send_payload(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            alerts = payload.get("alerts", [])
            delivered = max(len(alerts), 1)
            with LOCK:
                STATE["alert_notifications_total"] += delivered
            print(json.dumps({"alert_webhook": payload}, separators=(",", ":")), flush=True)
            self.send_payload(200, {"received": delivered})
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_payload(400, {"error": str(exc)})


if __name__ == "__main__":
    host = os.getenv("LISTEN_ADDRESS", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(json.dumps({"event": "starting", "host": host, "port": port}), flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
