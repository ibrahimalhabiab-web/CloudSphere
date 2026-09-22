# CloudSphere Demo Control

CloudSphere Demo Control replaces terminal-only order and error generation with a presentation-ready browser interface. It runs inside the existing `demo-app` container and uses the same simulation endpoints and Prometheus metrics as the original commands.

## Presentation URL

After starting the existing monitoring SSH tunnel, open:

```text
http://127.0.0.1:8000
```

The page includes direct links to:

- Grafana: `http://127.0.0.1:3000`
- Prometheus Alerts: `http://127.0.0.1:9090/alerts`
- Alertmanager: `http://127.0.0.1:9093`

## Controls

| Control | Result |
|---|---|
| **Create order** | Creates an order using the entered amount and quantity. |
| **Generate 3 demo orders** | Creates orders for 125, 250, and 75, producing 450 total revenue and using four inventory units. |
| **Restock +50** | Adds 50 units to the simulated inventory. |
| **Send one test error** | Generates one intentional HTTP 500 response. |
| **Trigger alert sequence** | Generates 20 intentional HTTP 500 responses at one-second intervals. |
| **Stop** | Stops the active error sequence after the current request. |
| **Reset all metrics** | Resets orders, revenue, inventory, errors, alert notifications, and HTTP counters. |

## Expected demonstration sequence

1. Select **Reset all metrics**.
2. Select **Generate 3 demo orders**.
3. Show Grafana changing to orders `3`, revenue `450`, and inventory `96` after approximately 2–4 seconds.
4. Select **Trigger alert sequence**.
5. Open Prometheus Alerts and show `DemoApplicationHighErrorRate` change from `INACTIVE` to `PENDING` to `FIRING`, normally within approximately 12–18 seconds.
6. Select **Reset all metrics**.
7. Wait approximately 30–45 seconds for the thirty-second error-rate window to clear.
8. Create one Standard order if `DemoNoRecentOrders` is active after the reset.

## Deploy the update from Kali

The following commands assume the complete updated project is located at `$HOME/Downloads/Cloud_Project`.

```bash
export PROJECT_DIR="$HOME/Downloads/Cloud_Project"
export ADMIN_USER="$(terraform -chdir="$PROJECT_DIR/terraform" output -raw admin_username)"
export MONITORING_IP="$(terraform -chdir="$PROJECT_DIR/terraform" output -raw public_ip_address)"
```

Copy only the updated application, Prometheus configuration, alert rules, and Grafana dashboard to the monitoring VM:

```bash
tar -C "$PROJECT_DIR/stack" -czf - \
  demo-app \
  compose.yaml \
  alertmanager/alertmanager.yml \
  prometheus/prometheus.yml \
  prometheus/rules/recording.yml \
  prometheus/rules/alerts.yml \
  grafana/dashboards/operations-overview.json \
| ssh "$ADMIN_USER@$MONITORING_IP" \
  'tar -xzf - -C /opt/monitoring'
```

Rebuild the demo application and reload the monitoring services:

```bash
ssh "$ADMIN_USER@$MONITORING_IP" '
  cd /opt/monitoring &&
  docker compose --env-file .env up -d --build demo-app &&
  docker compose --env-file .env up -d --force-recreate prometheus alertmanager grafana &&
  docker compose --env-file .env ps demo-app prometheus alertmanager grafana
'
```

Validate the application and Prometheus rules:

```bash
ssh "$ADMIN_USER@$MONITORING_IP" '
  curl -fsS http://127.0.0.1:8000/health &&
  cd /opt/monitoring &&
  docker compose --env-file .env exec -T prometheus \
    promtool check rules /etc/prometheus/rules/recording.yml /etc/prometheus/rules/alerts.yml
'
```

Expected results include a JSON health response containing `"status":"ok"` and a successful `promtool` rule check.

## Safe operating notes

- The HTTP 500 responses are intentional demonstration events. They do not stop the application.
- Keep port `8000` bound to host loopback and access it through the existing SSH tunnel.
- Do not use `docker compose down -v`; it can remove persistent volumes.
- Resetting clears the current counters but does not erase historical Prometheus samples already stored on disk.
