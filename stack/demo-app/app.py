#!/usr/bin/env python3
"""Dependency-free CloudSphere demonstration service and control console."""

from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse


START_TIME = time.time()
LOCK = threading.Lock()
STRESS_DURATION_SECONDS = 30
STRESS_COOLDOWN_SECONDS = 10
STRESS_PROCESS = None
STRESS_GENERATION = 0
CPU_STRESS_WORKER = r"""
import os
import sys
import time

try:
    os.nice(10)
except (AttributeError, OSError):
    pass

deadline = time.monotonic() + float(sys.argv[1])
value = 1
while time.monotonic() < deadline:
    value = (value * 1664525 + 1013904223) & 0xFFFFFFFF
"""
INITIAL_STATE = {
    "orders_total": 0,
    "revenue_total": 0.0,
    "inventory_level": 100,
    "application_errors_total": 0,
    "alert_notifications_total": 0,
    "cpu_stress_active": 0,
    "cpu_stress_runs_total": 0,
    "cpu_stress_started_at": 0.0,
    "cpu_stress_ends_at": 0.0,
    "cpu_stress_cooldown_until": 0.0,
}
STATE = dict(INITIAL_STATE)
REQUESTS = defaultdict(int)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
BRAND_AVATAR_URL = "/assets/cloudsphere-avatar.png"
BRAND_AVATAR_PATH = os.path.join(APP_DIR, "assets", "cloudsphere-avatar.png")


DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#091426">
  <title>CloudSphere Demo Control</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #061326;
      --bg-deep: #07182d;
      --bg-indigo: #17183f;
      --surface: rgba(15, 32, 55, 0.92);
      --surface-strong: #132743;
      --line: rgba(73, 110, 153, 0.34);
      --line-active: #496e99;
      --text: #f4f8ff;
      --text-secondary: #b9c7de;
      --muted: #93a6c2;
      --cyan: #2bc3e8;
      --cyan-light: #65d9f4;
      --blue: #5b8cff;
      --indigo: #3948a6;
      --violet: #9b8cff;
      --green: #48d6a0;
      --amber: #f6c85f;
      --red: #ff7a90;
      --shadow: 0 24px 60px rgba(1, 7, 18, 0.38);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 12% 0%, rgba(43, 195, 232, 0.16), transparent 34rem),
        radial-gradient(circle at 88% 12%, rgba(57, 72, 166, 0.28), transparent 38rem),
        linear-gradient(135deg, var(--bg) 0%, #081426 54%, var(--bg-indigo) 100%);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(101, 217, 244, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(101, 217, 244, 0.025) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 90%);
    }

    a { color: inherit; }
    button, input { font: inherit; }

    button:focus-visible, input:focus-visible, a:focus-visible {
      outline: 3px solid var(--cyan-light);
      outline-offset: 3px;
    }

    .shell {
      position: relative;
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 30px;
    }

    .brand { display: flex; align-items: center; gap: 15px; }

    .logo {
      position: relative;
      display: grid;
      place-items: center;
      width: 60px;
      height: 60px;
      flex: 0 0 60px;
    }

    .logo::before {
      content: "";
      position: absolute;
      inset: 10%;
      border-radius: 50%;
      background: rgba(43, 195, 232, 0.13);
      filter: blur(16px);
    }

    .logo img {
      position: relative;
      z-index: 1;
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
      filter: drop-shadow(0 0 14px rgba(43, 195, 232, 0.24));
    }

    .brand-name { color: var(--text); font-size: 1.18rem; font-weight: 780; letter-spacing: -0.02em; }

    .brand-subtitle {
      color: var(--muted);
      font-size: 0.79rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .connection {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      padding: 9px 13px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(15, 32, 55, 0.78);
      color: var(--text-secondary);
      font-size: 0.84rem;
    }

    .connection-dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--amber);
      box-shadow: 0 0 0 5px rgba(251, 191, 36, 0.1);
    }

    .connection.online .connection-dot {
      background: var(--green);
      box-shadow: 0 0 0 5px rgba(72, 214, 160, 0.12), 0 0 18px rgba(72, 214, 160, 0.32);
    }

    .connection.online {
      border-color: rgba(72, 214, 160, 0.3);
      background: rgba(72, 214, 160, 0.1);
      color: #c7fbe8;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.35fr 0.65fr;
      gap: 24px;
      align-items: end;
      margin-bottom: 24px;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      color: var(--cyan);
      font-size: 0.78rem;
      font-weight: 750;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    h1 {
      max-width: 760px;
      margin: 0;
      font-size: clamp(2.4rem, 6vw, 4.8rem);
      line-height: 0.98;
      letter-spacing: -0.065em;
    }

    h1 span {
      color: var(--cyan-light);
      background: linear-gradient(90deg, #2bd3f0 0%, var(--blue) 58%, var(--violet) 100%);
      background-clip: text;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .hero p { max-width: 680px; margin: 18px 0 0; color: var(--text-secondary); font-size: 1rem; }
    .quick-links { display: grid; gap: 9px; }

    .quick-link {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 46px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 13px;
      background: rgba(15, 32, 55, 0.78);
      color: #e7effb;
      text-decoration: none;
      transition: 160ms ease;
    }

    .quick-link:hover {
      transform: translateX(2px);
      border-color: var(--cyan-light);
      background: var(--surface-strong);
      box-shadow: 0 10px 28px rgba(43, 195, 232, 0.09);
    }

    .quick-link small { color: var(--cyan-light); }

    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 22px;
    }

    .stat {
      position: relative;
      overflow: hidden;
      padding: 19px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: linear-gradient(145deg, rgba(19, 39, 67, 0.96), rgba(11, 27, 49, 0.94));
      box-shadow: var(--shadow);
    }

    .stat::after {
      content: "";
      position: absolute;
      right: -26px;
      bottom: -40px;
      width: 100px;
      height: 100px;
      border-radius: 50%;
      background: var(--accent, var(--blue));
      filter: blur(36px);
      opacity: 0.13;
    }

    .stat-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--muted);
      font-size: 0.79rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .stat-icon {
      display: grid;
      place-items: center;
      width: 30px;
      height: 30px;
      border-radius: 10px;
      background: color-mix(in srgb, var(--accent, var(--blue)) 15%, transparent);
      color: var(--accent, var(--blue));
      font-size: 0.95rem;
    }

    .stat-value {
      position: relative;
      z-index: 1;
      margin-top: 10px;
      font-size: clamp(1.9rem, 4vw, 2.7rem);
      font-weight: 780;
      letter-spacing: -0.045em;
    }

    .stat-note { color: #8291a8; font-size: 0.78rem; }

    .workspace {
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 18px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: var(--surface);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }

    .panel-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 22px 16px;
      border-bottom: 1px solid var(--line);
    }

    .panel-title { margin: 0; font-size: 1.05rem; letter-spacing: -0.02em; }
    .panel-copy { margin: 4px 0 0; color: var(--muted); font-size: 0.84rem; }

    .step-badge {
      flex: 0 0 auto;
      padding: 5px 9px;
      border: 1px solid rgba(96, 165, 250, 0.22);
      border-radius: 999px;
      background: rgba(59, 130, 246, 0.09);
      color: #93c5fd;
      font-size: 0.72rem;
      font-weight: 750;
      letter-spacing: 0.07em;
      text-transform: uppercase;
    }

    .panel-body { padding: 20px 22px 22px; }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--text-secondary);
      font-size: 0.8rem;
      font-weight: 650;
    }

    input {
      width: 100%;
      height: 45px;
      padding: 0 13px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(4, 15, 31, 0.8);
      color: var(--text);
      transition: 160ms ease;
    }

    input:hover, input:focus {
      border-color: var(--cyan-light);
      background: rgba(7, 24, 45, 0.92);
    }

    .button-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; }

    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 43px;
      padding: 0 15px;
      border: 1px solid transparent;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 730;
      transition: 160ms ease;
    }

    .button:hover:not(:disabled) { transform: translateY(-2px); }
    .button:disabled { cursor: not-allowed; opacity: 0.52; }

    .button-primary {
      background: linear-gradient(135deg, var(--cyan), var(--blue));
      color: #071326;
      box-shadow: 0 10px 24px rgba(43, 195, 232, 0.2);
    }

    .button-secondary { border-color: var(--line); background: rgba(19, 39, 67, 0.78); color: #e7effb; }

    .button-danger {
      background: linear-gradient(135deg, #fb7185, #e11d48);
      color: white;
      box-shadow: 0 10px 24px rgba(225, 29, 72, 0.18);
    }

    .button-load {
      background: linear-gradient(135deg, var(--cyan), var(--violet));
      color: #061326;
      box-shadow: 0 10px 24px rgba(91, 140, 255, 0.2);
    }

    .button-reset {
      border-color: rgba(251, 191, 36, 0.28);
      background: rgba(120, 76, 12, 0.23);
      color: #fde68a;
    }

    .divider { height: 1px; margin: 21px 0; background: var(--line); }
    .section-label { margin-bottom: 11px; color: #e7effb; font-size: 0.85rem; font-weight: 700; }

    .preset-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }

    .preset {
      min-height: 62px;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(8, 25, 47, 0.72);
      color: #e7effb;
      cursor: pointer;
      transition: 160ms ease;
    }

    .preset:hover { border-color: var(--cyan-light); background: var(--surface-strong); }
    .preset strong, .preset small { display: block; }
    .preset small { margin-top: 2px; color: var(--muted); }

    .alert-card {
      padding: 15px;
      border: 1px solid rgba(251, 113, 133, 0.18);
      border-radius: 15px;
      background: linear-gradient(135deg, rgba(91, 20, 45, 0.22), rgba(49, 19, 48, 0.14));
    }

    .alert-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .alert-title { font-weight: 760; }
    .alert-time { color: #fda4af; font-size: 0.76rem; }
    .alert-card p { margin: 7px 0 0; color: #aebbd0; font-size: 0.82rem; }

    .stress-card {
      border-color: rgba(43, 195, 232, 0.24);
      background: linear-gradient(135deg, rgba(21, 94, 117, 0.2), rgba(57, 72, 166, 0.18));
      transition: border-color 180ms ease, box-shadow 180ms ease;
    }

    .stress-card.active {
      border-color: rgba(255, 122, 144, 0.5);
      box-shadow: inset 0 0 28px rgba(255, 122, 144, 0.08), 0 0 28px rgba(91, 140, 255, 0.12);
    }

    .stress-card .alert-time { color: var(--cyan-light); }
    .stress-card.active .alert-time { color: #fda4af; }

    .stress-progress {
      background: linear-gradient(90deg, var(--cyan), var(--violet), var(--red));
    }

    .safety-note {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.74rem;
    }

    .safety-note strong { color: var(--green); white-space: nowrap; }

    .progress-shell {
      overflow: hidden;
      height: 8px;
      margin-top: 14px;
      border-radius: 999px;
      background: rgba(2, 6, 23, 0.66);
    }

    .progress {
      width: 0;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #fb7185, #f97316);
      transition: width 220ms ease;
    }

    .progress-meta { display: flex; justify-content: space-between; gap: 12px; margin-top: 8px; color: var(--muted); font-size: 0.76rem; }
    .timeline { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 17px; }

    .timeline-step {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 11px;
      background: rgba(8, 19, 35, 0.5);
      text-align: center;
    }

    .timeline-step strong { display: block; color: #e7effb; font-size: 0.72rem; }
    .timeline-step small { color: var(--muted); font-size: 0.68rem; }
    .log-panel { grid-column: 1 / -1; }

    .log-list {
      display: grid;
      gap: 8px;
      max-height: 220px;
      overflow: auto;
      padding-right: 4px;
    }

    .log-item {
      display: grid;
      grid-template-columns: 72px 86px 1fr;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border: 1px solid rgba(148, 163, 184, 0.1);
      border-radius: 11px;
      background: rgba(5, 13, 26, 0.5);
      font-size: 0.79rem;
    }

    .log-time { color: #64748b; font-variant-numeric: tabular-nums; }
    .log-kind { color: #7dd3fc; font-weight: 720; text-transform: uppercase; }
    .log-kind.error { color: #fda4af; }
    .log-kind.success { color: #6ee7b7; }
    .log-message { color: var(--text-secondary); }

    .footer { display: flex; justify-content: space-between; gap: 20px; margin-top: 20px; color: #64748b; font-size: 0.75rem; }

    .toast {
      position: fixed;
      right: 22px;
      bottom: 22px;
      z-index: 20;
      max-width: min(390px, calc(100% - 44px));
      padding: 13px 15px;
      border: 1px solid rgba(52, 211, 153, 0.28);
      border-radius: 13px;
      background: rgba(6, 37, 35, 0.96);
      color: #d1fae5;
      box-shadow: var(--shadow);
      opacity: 0;
      transform: translateY(16px);
      pointer-events: none;
      transition: 180ms ease;
    }

    .toast.visible { opacity: 1; transform: translateY(0); }
    .toast.error { border-color: rgba(251, 113, 133, 0.3); background: rgba(61, 16, 34, 0.97); color: #ffe4e6; }

    @media (max-width: 900px) {
      .hero, .workspace { grid-template-columns: 1fr; }
      .quick-links { grid-template-columns: repeat(3, 1fr); }
      .quick-link { align-items: flex-start; flex-direction: column; justify-content: center; }
      .stats { grid-template-columns: repeat(2, 1fr); }
    }

    @media (max-width: 610px) {
      .shell { width: min(100% - 20px, 1180px); padding-top: 16px; }
      .topbar { align-items: flex-start; }
      .brand { gap: 11px; }
      .logo { width: 48px; height: 48px; flex-basis: 48px; }
      .connection { position: relative; padding: 8px 10px; }
      .connection span:last-child {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }
      .hero { margin-top: 14px; }
      h1 { font-size: 2.65rem; }
      .quick-links, .stats, .form-grid, .preset-grid { grid-template-columns: 1fr; }
      .quick-link { flex-direction: row; align-items: center; }
      .hero > *, .workspace > *, .stats > *, .panel-header > *, .alert-head > *, .progress-meta > *, .log-item > * { min-width: 0; }
      .panel, .panel-header, .panel-body, .alert-card, .log-panel { min-width: 0; max-width: 100%; }
      .button { max-width: 100%; white-space: normal; }
      .timeline { grid-template-columns: 1fr; }
      .log-item { grid-template-columns: 63px 74px 1fr; gap: 7px; }
      .footer { flex-direction: column; }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="logo" aria-hidden="true">
          <img src="/assets/cloudsphere-avatar.png" alt="">
        </div>
        <div>
          <div class="brand-name">CloudSphere</div>
          <div class="brand-subtitle">Demo control</div>
        </div>
      </div>
      <div id="connection" class="connection" role="status" aria-live="polite">
        <span class="connection-dot"></span>
        <span id="connection-text">Connecting to service</span>
      </div>
    </header>

    <section class="hero">
      <div>
        <div class="eyebrow">Live presentation console</div>
        <h1>Operate. Observe. <span>Respond.</span></h1>
        <p>Create business activity, generate a controlled failure, and reset the environment while CloudSphere synchronizes every event with Prometheus and Grafana.</p>
      </div>
      <nav class="quick-links" aria-label="Monitoring tools">
        <a id="grafana-link" class="quick-link" href="http://127.0.0.1:3000" target="_blank" rel="noreferrer"><span>Grafana</span><small>Dashboard &nearr;</small></a>
        <a id="prometheus-link" class="quick-link" href="http://127.0.0.1:9090/alerts" target="_blank" rel="noreferrer"><span>Prometheus</span><small>Alerts &nearr;</small></a>
        <a id="alertmanager-link" class="quick-link" href="http://127.0.0.1:9093" target="_blank" rel="noreferrer"><span>Alertmanager</span><small>Incidents &nearr;</small></a>
      </nav>
    </section>

    <section class="stats" aria-label="Live business metrics">
      <article class="stat" style="--accent: var(--cyan)">
        <div class="stat-label">Orders <span class="stat-icon">#</span></div>
        <div id="orders-value" class="stat-value">0</div>
        <div class="stat-note">accepted transactions</div>
      </article>
      <article class="stat" style="--accent: var(--green)">
        <div class="stat-label">Revenue <span class="stat-icon">$</span></div>
        <div id="revenue-value" class="stat-value">$0.00</div>
        <div class="stat-note">simulated total</div>
      </article>
      <article class="stat" style="--accent: var(--amber)">
        <div class="stat-label">Inventory <span class="stat-icon">&#9638;</span></div>
        <div id="inventory-value" class="stat-value">100</div>
        <div class="stat-note">units available</div>
      </article>
      <article class="stat" style="--accent: var(--red)">
        <div class="stat-label">Errors <span class="stat-icon">!</span></div>
        <div id="errors-value" class="stat-value">0</div>
        <div class="stat-note">controlled HTTP 500 events</div>
      </article>
    </section>

    <section class="workspace">
      <article class="panel">
        <header class="panel-header">
          <div>
            <h2 class="panel-title">Order simulator</h2>
            <p class="panel-copy">Create transactions and watch the business panels move.</p>
          </div>
          <span class="step-badge">Step 1</span>
        </header>
        <div class="panel-body">
          <form id="order-form">
            <div class="form-grid">
              <label>Order amount
                <input id="order-amount" type="number" min="0.01" step="0.01" value="125" required>
              </label>
              <label>Quantity
                <input id="order-quantity" type="number" min="1" step="1" value="1" required>
              </label>
            </div>
            <div class="button-row">
              <button id="create-order" class="button button-primary" type="submit">Create order</button>
              <button id="demo-orders" class="button button-secondary" type="button">Generate 3 demo orders</button>
              <button id="restock" class="button button-secondary" type="button">Restock +50</button>
            </div>
          </form>

          <div class="divider"></div>
          <div class="section-label">Quick order presets</div>
          <div class="preset-grid">
            <button class="preset" type="button" data-amount="75" data-quantity="1"><strong>Starter</strong><small>$75 / 1 unit</small></button>
            <button class="preset" type="button" data-amount="125" data-quantity="1"><strong>Standard</strong><small>$125 / 1 unit</small></button>
            <button class="preset" type="button" data-amount="250" data-quantity="2"><strong>Premium</strong><small>$250 / 2 units</small></button>
          </div>

          <div class="divider"></div>
          <div class="section-label">Presentation reset</div>
          <p class="panel-copy">Return the demo counters to their starting values and stop any active load test.</p>
          <div class="button-row">
            <button id="reset-all" class="button button-reset" type="button">Reset all metrics</button>
          </div>
        </div>
      </article>

      <article class="panel">
        <header class="panel-header">
          <div>
            <h2 class="panel-title">Reliability test</h2>
            <p class="panel-copy">Generate controlled application errors or a safe infrastructure CPU pulse.</p>
          </div>
          <span class="step-badge">Step 2</span>
        </header>
        <div class="panel-body">
          <div class="alert-card">
            <div class="alert-head">
              <span class="alert-title">High-error alert sequence</span>
              <span class="alert-time">~8 seconds</span>
            </div>
            <p>Sends 20 intentional HTTP 500 responses over eight seconds. Prometheus and Grafana show the alert moving from pending to firing while the application stays healthy.</p>
            <div class="progress-shell" aria-hidden="true"><div id="error-progress" class="progress"></div></div>
            <div class="progress-meta"><span id="error-progress-text">Ready to start</span><span id="error-progress-count">0 / 20</span></div>
          </div>

          <div class="button-row">
            <button id="start-errors" class="button button-danger" type="button">Trigger alert sequence</button>
            <button id="single-error" class="button button-secondary" type="button">Send one test error</button>
            <button id="stop-errors" class="button button-secondary" type="button" disabled>Stop</button>
          </div>

          <div class="timeline" aria-label="Expected alert progression">
            <div class="timeline-step"><strong>INACTIVE</strong><small>normal baseline</small></div>
            <div class="timeline-step"><strong>PENDING</strong><small>condition detected</small></div>
            <div class="timeline-step"><strong>FIRING</strong><small>alert confirmed</small></div>
          </div>

          <div class="divider"></div>
          <div class="section-label">Infrastructure pulse</div>
          <div id="stress-card" class="alert-card stress-card">
            <div class="alert-head">
              <span class="alert-title">Controlled server-load test</span>
              <span id="stress-state" class="alert-time">READY</span>
            </div>
            <p>Runs one low-priority CPU worker for 30 seconds. Watch Peak Host CPU, Container CPU, Server Load, and Active Platform Alerts react in real time.</p>
            <div class="progress-shell" aria-hidden="true"><div id="stress-progress" class="progress stress-progress"></div></div>
            <div class="progress-meta"><span id="stress-progress-text">Ready to start</span><span id="stress-progress-count">0 / 30s</span></div>
            <div class="safety-note"><strong>SAFE MODE</strong><span>CPU only, container-capped, one run at a time, and automatic recovery. No disk, memory, GitLab, or stored data is modified.</span></div>
          </div>

          <div class="button-row">
            <button id="start-stress" class="button button-load" type="button">Run 30-second server load</button>
            <button id="stop-stress" class="button button-secondary" type="button" disabled>Stop &amp; recover</button>
          </div>

          <div class="divider"></div>
          <div class="section-label">What to show your audience</div>
          <p class="panel-copy">Keep this console and the live 15-minute Grafana view side by side. The error drill demonstrates application alerting; Infrastructure Pulse demonstrates real container and host CPU pressure. Reset to stop every drill and show recovery.</p>
        </div>
      </article>

      <article class="panel log-panel">
        <header class="panel-header">
          <div>
            <h2 class="panel-title">Presentation activity</h2>
            <p class="panel-copy">A local event trail for the actions performed from this screen.</p>
          </div>
          <span id="request-count" class="step-badge">0 HTTP events</span>
        </header>
        <div class="panel-body">
          <div id="activity-log" class="log-list" aria-live="polite">
            <div class="log-item"><span class="log-time">--:--:--</span><span class="log-kind">system</span><span class="log-message">Waiting for the demo service.</span></div>
          </div>
        </div>
      </article>
    </section>

    <footer class="footer">
      <span>CloudSphere &middot; Complete visibility. Total control.</span>
      <span id="uptime">Service uptime: --</span>
    </footer>
  </main>

  <div id="toast" class="toast" role="status" aria-live="polite"></div>

  <script>
    const byId = (id) => document.getElementById(id);
    const activity = [];
    let toastTimer;
    let burstRunning = false;
    let burstCancelled = false;
    let stressActive = false;

    function configureLinks() {
      const host = window.location.hostname || "127.0.0.1";
      const protocol = window.location.protocol === "https:" ? "https:" : "http:";
      byId("grafana-link").href = `${protocol}//${host}:3000/d/internal-ops-overview/cloudsphere-infrastructure-command-center?orgId=1&from=now-15m&to=now&timezone=browser&refresh=2s`;
      byId("prometheus-link").href = `${protocol}//${host}:9090/alerts`;
      byId("alertmanager-link").href = `${protocol}//${host}:9093`;
    }

    function formatTime(date = new Date()) {
      return date.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
    }

    function formatDuration(seconds) {
      seconds = Math.max(0, Math.floor(seconds));
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainder = seconds % 60;
      return [hours, minutes, remainder].map((value) => String(value).padStart(2, "0")).join(":");
    }

    function addActivity(kind, message) {
      activity.unshift({time: formatTime(), kind, message});
      activity.splice(8);
      byId("activity-log").innerHTML = activity.map((entry) => `
        <div class="log-item">
          <span class="log-time">${entry.time}</span>
          <span class="log-kind ${entry.kind}">${entry.kind}</span>
          <span class="log-message">${entry.message}</span>
        </div>`).join("");
    }

    function showToast(message, isError = false) {
      const toast = byId("toast");
      toast.textContent = message;
      toast.classList.toggle("error", isError);
      toast.classList.add("visible");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove("visible"), 3200);
    }

    function setConnection(online) {
      byId("connection").classList.toggle("online", online);
      byId("connection-text").textContent = online ? "Demo service connected" : "Service connection lost";
    }

    function updateState(payload) {
      const state = payload.state;
      byId("orders-value").textContent = state.orders_total.toLocaleString();
      byId("revenue-value").textContent = `$${Number(state.revenue_total).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      byId("inventory-value").textContent = state.inventory_level.toLocaleString();
      byId("errors-value").textContent = state.application_errors_total.toLocaleString();
      byId("request-count").textContent = `${payload.http.requests_total.toLocaleString()} HTTP events`;
      byId("uptime").textContent = `Service uptime: ${formatDuration(payload.service.uptime_seconds)}`;
      updateStressState(payload.stress || {});
    }

    function updateStressState(stress) {
      const duration = Number(stress.duration_seconds || 30);
      const remaining = Math.max(0, Number(stress.remaining_seconds || 0));
      const cooldown = Math.max(0, Number(stress.cooldown_remaining_seconds || 0));
      const elapsed = stress.active ? Math.max(0, duration - remaining) : 0;
      stressActive = Boolean(stress.active);

      byId("stress-card").classList.toggle("active", stressActive);
      byId("stress-progress").style.width = `${stressActive ? Math.min(100, (elapsed / duration) * 100) : 0}%`;
      byId("stress-progress-count").textContent = stressActive ? `${Math.ceil(elapsed)} / ${duration}s` : `0 / ${duration}s`;
      byId("start-stress").disabled = stressActive || cooldown > 0;
      byId("stop-stress").disabled = !stressActive;

      if (stressActive) {
        byId("stress-state").textContent = remaining > 22 ? "RAMPING" : "ACTIVE";
        byId("stress-progress-text").textContent = `${Math.ceil(remaining)} seconds until automatic recovery`;
      } else if (cooldown > 0) {
        byId("stress-state").textContent = "RECOVERING";
        byId("stress-progress-text").textContent = `Metrics cooling down · retry in ${Math.ceil(cooldown)}s`;
      } else {
        byId("stress-state").textContent = "READY";
        byId("stress-progress-text").textContent = "Ready to start";
      }
    }

    async function readJson(response) {
      try { return await response.json(); }
      catch (_) { return {}; }
    }

    async function refreshState(silent = true) {
      try {
        const response = await fetch("/api/state", {cache: "no-store"});
        if (!response.ok) throw new Error(`State request failed (${response.status})`);
        updateState(await response.json());
        setConnection(true);
      } catch (error) {
        setConnection(false);
        if (!silent) showToast(error.message, true);
      }
    }

    async function createOrder(amount, quantity, announce = true) {
      const response = await fetch(`/simulate/order?amount=${encodeURIComponent(amount)}&quantity=${encodeURIComponent(quantity)}`, {cache: "no-store"});
      const payload = await readJson(response);
      if (!response.ok) throw new Error(payload.error || `Order failed (${response.status})`);
      if (announce) {
        addActivity("success", `Order accepted: $${Number(amount).toFixed(2)}, ${quantity} unit${Number(quantity) === 1 ? "" : "s"}.`);
        showToast("Order created and sent to Prometheus.");
      }
      await refreshState();
      return payload;
    }

    async function sendError(announce = true) {
      const response = await fetch("/simulate/error", {cache: "no-store"});
      const payload = await readJson(response);
      if (response.status !== 500) throw new Error(payload.error || `Unexpected response (${response.status})`);
      if (announce) {
        addActivity("error", "One controlled HTTP 500 error generated.");
        showToast("Controlled error generated.");
      }
      await refreshState();
    }

    function updateProgress(current, total, text) {
      const percent = total ? Math.round((current / total) * 100) : 0;
      byId("error-progress").style.width = `${percent}%`;
      byId("error-progress-count").textContent = `${current} / ${total}`;
      byId("error-progress-text").textContent = text;
    }

    const pause = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

    async function runErrorBurst() {
      if (burstRunning) return;
      burstRunning = true;
      burstCancelled = false;
      const total = 20;
      byId("start-errors").disabled = true;
      byId("single-error").disabled = true;
      byId("stop-errors").disabled = false;
      updateProgress(0, total, "Starting controlled failure");
      addActivity("system", "High-error alert sequence started: 20 errors at 400-millisecond intervals.");

      try {
        for (let current = 1; current <= total && !burstCancelled; current += 1) {
          await sendError(false);
          updateProgress(current, total, current === total ? "Sequence complete" : "Generating controlled errors");
          if (current < total && !burstCancelled) await pause(400);
        }
        if (burstCancelled) {
          addActivity("system", "Error sequence stopped by the presenter.");
          showToast("Error sequence stopped.");
        } else {
          addActivity("error", "Error sequence complete. Check Prometheus for PENDING or FIRING state.");
          showToast("Sequence complete. Open Prometheus Alerts.");
        }
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
      } finally {
        burstRunning = false;
        byId("start-errors").disabled = false;
        byId("single-error").disabled = false;
        byId("stop-errors").disabled = true;
      }
    }

    byId("order-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = byId("create-order");
      button.disabled = true;
      try {
        await createOrder(byId("order-amount").value, byId("order-quantity").value);
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
      } finally {
        button.disabled = false;
      }
    });

    document.querySelectorAll(".preset").forEach((button) => {
      button.addEventListener("click", () => {
        byId("order-amount").value = button.dataset.amount;
        byId("order-quantity").value = button.dataset.quantity;
        byId("order-amount").focus();
      });
    });

    byId("demo-orders").addEventListener("click", async () => {
      const button = byId("demo-orders");
      button.disabled = true;
      try {
        for (const order of [{amount: 125, quantity: 1}, {amount: 250, quantity: 2}, {amount: 75, quantity: 1}]) {
          await createOrder(order.amount, order.quantity, false);
          await pause(400);
        }
        addActivity("success", "Three demo orders created: $450 revenue and four inventory units used.");
        showToast("Three demo orders created.");
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
      } finally {
        button.disabled = false;
      }
    });

    byId("restock").addEventListener("click", async () => {
      try {
        const response = await fetch("/simulate/restock?quantity=50", {cache: "no-store"});
        const payload = await readJson(response);
        if (!response.ok) throw new Error(payload.error || "Restock failed");
        addActivity("success", "Inventory restocked by 50 units.");
        showToast("Inventory restocked.");
        await refreshState();
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
      }
    });

    byId("reset-all").addEventListener("click", async () => {
      burstCancelled = true;
      try {
        const response = await fetch("/simulate/reset", {method: "POST", cache: "no-store"});
        const payload = await readJson(response);
        if (!response.ok) throw new Error(payload.error || "Reset failed");
        updateProgress(0, 20, "Ready to start");
        addActivity("success", "All demonstration counters reset to their starting values.");
        showToast("CloudSphere demonstration reset.");
        await refreshState();
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
      }
    });

    byId("start-errors").addEventListener("click", runErrorBurst);
    byId("single-error").addEventListener("click", async () => {
      try { await sendError(true); }
      catch (error) { addActivity("error", error.message); showToast(error.message, true); }
    });
    byId("stop-errors").addEventListener("click", () => { burstCancelled = true; });

    byId("start-stress").addEventListener("click", async () => {
      const button = byId("start-stress");
      button.disabled = true;
      try {
        const response = await fetch("/simulate/load/start", {
          method: "POST",
          cache: "no-store",
          headers: {"X-CloudSphere-Demo": "1"},
        });
        const payload = await readJson(response);
        if (!response.ok) throw new Error(payload.error || `Load test failed (${response.status})`);
        addActivity("system", "Infrastructure Pulse started: capped CPU load for 30 seconds.");
        showToast("Server load started. Open the live Grafana dashboard.");
        await refreshState();
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
        await refreshState();
      }
    });

    byId("stop-stress").addEventListener("click", async () => {
      const button = byId("stop-stress");
      button.disabled = true;
      try {
        const response = await fetch("/simulate/load/stop", {
          method: "POST",
          cache: "no-store",
          headers: {"X-CloudSphere-Demo": "1"},
        });
        const payload = await readJson(response);
        if (!response.ok) throw new Error(payload.error || `Stop failed (${response.status})`);
        addActivity("success", "Infrastructure Pulse stopped. Prometheus is clearing its short rate window.");
        showToast("Load stopped. Grafana will return to baseline shortly.");
        await refreshState();
      } catch (error) {
        addActivity("error", error.message);
        showToast(error.message, true);
        await refreshState();
      }
    });

    async function scheduleStateRefresh() {
      await refreshState(true);
      window.setTimeout(scheduleStateRefresh, stressActive ? 750 : 2000);
    }

    configureLinks();
    addActivity("system", "CloudSphere presentation console opened.");
    refreshState(false);
    window.setTimeout(scheduleStateRefresh, 1000);
  </script>
</body>
</html>
""".encode("utf-8")


def json_bytes(payload):
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def metric_label(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class StressAlreadyRunningError(RuntimeError):
    """Raised when a second controlled CPU load is requested."""


class StressCooldownError(RuntimeError):
    """Raised when a new controlled CPU load is requested during recovery."""


def _stress_payload_locked(now=None):
    """Build the UI-safe controlled-load state while LOCK is held."""
    now = time.time() if now is None else now
    active = bool(STATE["cpu_stress_active"])
    remaining = max(0, math.ceil(STATE["cpu_stress_ends_at"] - now)) if active else 0
    cooldown = max(0, math.ceil(STATE["cpu_stress_cooldown_until"] - now)) if not active else 0
    return {
        "active": active,
        "duration_seconds": STRESS_DURATION_SECONDS,
        "remaining_seconds": remaining,
        "cooldown_remaining_seconds": cooldown,
        "workers": 1 if active else 0,
        "runs_total": STATE["cpu_stress_runs_total"],
        "auto_stop": True,
    }


def _clear_stress_locked(start_cooldown=True):
    """Clear controlled-load state while LOCK is held."""
    STATE["cpu_stress_active"] = 0
    STATE["cpu_stress_started_at"] = 0.0
    STATE["cpu_stress_ends_at"] = 0.0
    STATE["cpu_stress_cooldown_until"] = (
        time.time() + STRESS_COOLDOWN_SECONDS if start_cooldown else 0.0
    )


def _launch_cpu_stress_worker():
    """Start one fixed, low-priority CPU worker without invoking a shell."""
    return subprocess.Popen(
        [sys.executable, "-c", CPU_STRESS_WORKER, str(STRESS_DURATION_SECONDS)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )


def _terminate_process(process):
    """Stop and reap a controlled worker, escalating only if it does not exit."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _watch_cpu_stress(generation, process):
    """Reap a naturally completed worker and move the drill into recovery."""
    global STRESS_PROCESS
    process.wait()
    with LOCK:
        if generation == STRESS_GENERATION and STRESS_PROCESS is process:
            STRESS_PROCESS = None
            _clear_stress_locked(start_cooldown=True)


def _start_cpu_stress_watcher(generation, process):
    threading.Thread(
        target=_watch_cpu_stress,
        args=(generation, process),
        name="cloudsphere-cpu-stress-watcher",
        daemon=True,
    ).start()


def start_controlled_cpu_load():
    """Start the bounded presentation CPU pulse and return its server state."""
    global STRESS_GENERATION, STRESS_PROCESS
    now = time.time()
    with LOCK:
        if STATE["cpu_stress_active"]:
            raise StressAlreadyRunningError("A controlled server-load test is already running.")
        cooldown = math.ceil(STATE["cpu_stress_cooldown_until"] - now)
        if cooldown > 0:
            raise StressCooldownError(f"Recovery is still in progress. Try again in {cooldown} seconds.")
        STRESS_GENERATION += 1
        generation = STRESS_GENERATION
        STATE["cpu_stress_active"] = 1
        STATE["cpu_stress_runs_total"] += 1
        STATE["cpu_stress_started_at"] = now
        STATE["cpu_stress_ends_at"] = now + STRESS_DURATION_SECONDS
        STATE["cpu_stress_cooldown_until"] = 0.0

    try:
        process = _launch_cpu_stress_worker()
    except OSError as exc:
        with LOCK:
            if generation == STRESS_GENERATION:
                _clear_stress_locked(start_cooldown=False)
        raise RuntimeError("The controlled CPU worker could not be started.") from exc

    with LOCK:
        if generation != STRESS_GENERATION or not STATE["cpu_stress_active"]:
            cancelled = True
        else:
            STRESS_PROCESS = process
            cancelled = False
            payload = _stress_payload_locked()

    if cancelled:
        _terminate_process(process)
        raise RuntimeError("The controlled server-load test was cancelled before it started.")

    _start_cpu_stress_watcher(generation, process)
    return payload


def stop_controlled_cpu_load(start_cooldown=True):
    """Stop the controlled CPU pulse. The operation is safe to repeat."""
    global STRESS_GENERATION, STRESS_PROCESS
    with LOCK:
        was_active = bool(STATE["cpu_stress_active"])
        STRESS_GENERATION += 1
        process = STRESS_PROCESS
        STRESS_PROCESS = None
        _clear_stress_locked(start_cooldown=start_cooldown and was_active)
        payload = _stress_payload_locked()
    _terminate_process(process)
    return payload


def reset_demo_state():
    """Return the in-memory demonstration counters to their initial values."""
    stop_controlled_cpu_load(start_cooldown=False)
    with LOCK:
        STATE.clear()
        STATE.update(INITIAL_STATE)
        REQUESTS.clear()
        return dict(STATE)


def create_order(amount, quantity):
    """Accept one simulated order and return the resulting state."""
    amount = float(amount)
    quantity = int(quantity)
    if amount <= 0 or quantity <= 0:
        raise ValueError("amount and quantity must be positive")
    with LOCK:
        if quantity > STATE["inventory_level"]:
            raise ValueError("insufficient simulated inventory")
        STATE["orders_total"] += 1
        STATE["revenue_total"] += amount
        STATE["inventory_level"] -= quantity
        return dict(STATE)


def restock_inventory(quantity):
    """Add units to the simulated inventory and return the new level."""
    quantity = int(quantity)
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    with LOCK:
        STATE["inventory_level"] += quantity
        return STATE["inventory_level"]


def simulate_application_error():
    """Increment the controlled application-error counter."""
    with LOCK:
        STATE["application_errors_total"] += 1
        return STATE["application_errors_total"]


def state_snapshot():
    """Return the current UI-safe state and aggregate HTTP counters."""
    with LOCK:
        state = dict(STATE)
        requests = dict(REQUESTS)
        stress = _stress_payload_locked()
    return {
        "state": state,
        "service": {
            "name": "CloudSphere Demo Control",
            "version": "2.2.0",
            "uptime_seconds": round(time.time() - START_TIME, 3),
        },
        "stress": stress,
        "http": {
            "requests_total": sum(requests.values()),
            "errors_5xx_total": sum(
                value for (_, _, status), value in requests.items() if status.startswith("5")
            ),
        },
    }


def render_metrics():
    with LOCK:
        snapshot = dict(STATE)
        requests = dict(REQUESTS)

    lines = [
        "# HELP demo_app_info Static information about the demonstration application.",
        "# TYPE demo_app_info gauge",
        'demo_app_info{service="order-demo",version="2.2.0"} 1',
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
        "# HELP cloudsphere_demo_cpu_stress_active Whether the controlled CPU presentation load is active.",
        "# TYPE cloudsphere_demo_cpu_stress_active gauge",
        f"cloudsphere_demo_cpu_stress_active {snapshot['cpu_stress_active']}",
        "# HELP cloudsphere_demo_cpu_stress_remaining_seconds Seconds remaining in the controlled CPU load.",
        "# TYPE cloudsphere_demo_cpu_stress_remaining_seconds gauge",
        f"cloudsphere_demo_cpu_stress_remaining_seconds {max(0, math.ceil(snapshot['cpu_stress_ends_at'] - time.time())) if snapshot['cpu_stress_active'] else 0}",
        "# HELP cloudsphere_demo_cpu_stress_runs_total Controlled CPU presentation loads started.",
        "# TYPE cloudsphere_demo_cpu_stress_runs_total counter",
        f"cloudsphere_demo_cpu_stress_runs_total {snapshot['cpu_stress_runs_total']}",
        "# HELP demo_http_requests_total HTTP requests processed by path and status.",
        "# TYPE demo_http_requests_total counter",
    ]
    for (method, path, status), value in sorted(requests.items()):
        labels = f'method="{metric_label(method)}",path="{metric_label(path)}",status="{metric_label(status)}"'
        lines.append(f"demo_http_requests_total{{{labels}}} {value}")
    return ("\n".join(lines) + "\n").encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "CloudSphereDemo/2.2"

    def log_message(self, fmt, *args):
        print(json.dumps({"time": time.time(), "client": self.client_address[0], "message": fmt % args}), flush=True)

    def record(self, status):
        path = urlparse(self.path).path
        with LOCK:
            REQUESTS[(self.command, path, str(status))] += 1

    def send_payload(self, status, payload, content_type="application/json; charset=utf-8", cache_control="no-store"):
        body = payload if isinstance(payload, bytes) else json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)
        self.record(status)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == BRAND_AVATAR_URL:
            try:
                with open(BRAND_AVATAR_PATH, "rb") as avatar_file:
                    avatar = avatar_file.read()
            except OSError:
                self.send_payload(404, {"error": "brand avatar not found"})
            else:
                self.send_payload(200, avatar, "image/png", "public, max-age=86400")
            return

        if parsed.path == "/":
            self.send_payload(200, DASHBOARD_HTML, "text/html; charset=utf-8")
            return

        if parsed.path == "/api/state":
            self.send_payload(200, state_snapshot())
            return

        if parsed.path == "/health":
            self.send_payload(200, {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 3)})
            return

        if parsed.path == "/metrics":
            self.send_payload(200, render_metrics(), "text/plain; version=0.0.4; charset=utf-8")
            return

        if parsed.path == "/simulate/order":
            try:
                amount = query.get("amount", ["100"])[0]
                quantity = query.get("quantity", ["1"])[0]
                snapshot = create_order(amount, quantity)
                self.send_payload(
                    200,
                    {"accepted": True, "amount": float(amount), "quantity": int(quantity), "state": snapshot},
                )
            except (TypeError, ValueError) as exc:
                self.send_payload(400, {"accepted": False, "error": str(exc)})
            return

        if parsed.path == "/simulate/restock":
            try:
                quantity = query.get("quantity", ["50"])[0]
                level = restock_inventory(quantity)
                self.send_payload(200, {"restocked": int(quantity), "inventory_level": level})
            except (TypeError, ValueError) as exc:
                self.send_payload(400, {"error": str(exc)})
            return

        if parsed.path == "/simulate/error":
            simulate_application_error()
            self.send_payload(500, {"status": "simulated failure"})
            return

        self.send_payload(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/simulate/reset":
            self.send_payload(200, {"reset": True, "state": reset_demo_state()})
            return

        if path in ("/simulate/load/start", "/simulate/load/stop"):
            if self.headers.get("X-CloudSphere-Demo") != "1":
                self.send_payload(403, {"accepted": False, "error": "Missing demonstration request header."})
                return
            if path == "/simulate/load/stop":
                self.send_payload(200, {"stopped": True, "stress": stop_controlled_cpu_load()})
                return
            try:
                stress = start_controlled_cpu_load()
                self.send_payload(202, {"accepted": True, "stress": stress})
            except StressAlreadyRunningError as exc:
                self.send_payload(409, {"accepted": False, "error": str(exc)})
            except StressCooldownError as exc:
                self.send_payload(429, {"accepted": False, "error": str(exc)})
            except RuntimeError as exc:
                self.send_payload(503, {"accepted": False, "error": str(exc)})
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
