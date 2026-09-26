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
| **Trigger alert sequence** | Generates 20 intentional HTTP 500 responses over approximately eight seconds. |
| **Stop** | Stops the active error sequence after the current request. |
| **Run 30-second server load** | Starts one low-priority, container-capped CPU worker so cAdvisor, Prometheus, Grafana, and the alert pipeline observe a real infrastructure change. |
| **Stop & recover** | Stops the CPU worker early and begins the short Prometheus recovery window. |
| **Reset all metrics** | Stops any active CPU load and resets orders, revenue, inventory, errors, alert notifications, and HTTP counters. |

## Expected demonstration sequence

1. Select **Reset all metrics**.
2. Select **Generate 3 demo orders**.
3. Select **Trigger alert sequence** and show `DemoApplicationHighErrorRate` change from `INACTIVE` to `PENDING` to `FIRING`, normally within approximately 6–10 seconds. The Grafana alert pipeline includes both pending and firing states.
4. Select **Reset all metrics** and allow approximately 10–15 seconds for the ten-second error-rate window to clear.
5. Open Grafana from the CloudSphere link. It forces **Last 15 minutes** and **Refresh 2s** for the presentation.
6. Select **Run 30-second server load**.
7. Show `monitoring-demo-app` rise in **Container CPU**, the monitoring host rise in **Peak Host CPU** and **Fleet Resource Utilization**, and `CloudSphereControlledCpuLoad` enter the alert pipeline.
8. Let the test stop automatically, or select **Stop & recover**, then show the graphs and alert return to baseline.

## Deploy the update from Kali

The following commands assume the complete updated project is located at `$HOME/Downloads/CloudSphere_GitLab`.

```bash
export PROJECT_DIR="$HOME/Downloads/CloudSphere_GitLab"
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
  grafana/provisioning/datasources/prometheus.yml \
  grafana/dashboards/operations-overview.json \
| ssh "$ADMIN_USER@$MONITORING_IP" \
  'tar -xzf - -C /opt/monitoring'
```

Rebuild the demo application and reload the monitoring services:

```bash
ssh "$ADMIN_USER@$MONITORING_IP" '
  cd /opt/monitoring &&
  docker compose --env-file .env up -d --build --force-recreate demo-app &&
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
- Infrastructure Pulse is limited to one low-priority worker, 0.80 CPU, 192 MB of memory, 64 processes, and 30 seconds. It never writes load data to disk.
- A ten-second cooldown prevents repeatedly stacking presentation load. **Reset all metrics** also terminates the worker.
- Keep port `8000` bound to host loopback and access it through the existing SSH tunnel.
- Do not use `docker compose down -v`; it can remove persistent volumes.
- Resetting clears the current counters but does not erase historical Prometheus samples already stored on disk.
