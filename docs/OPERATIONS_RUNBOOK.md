# Operations Runbook

## Platform access

Grafana is available on TCP 3000 only from the trusted administrator CIDR. Prometheus and Alertmanager should be accessed through SSH tunnels:

```bash
ssh -L 9090:127.0.0.1:9090 azureadmin@PUBLIC_IP
ssh -L 9093:127.0.0.1:9093 azureadmin@PUBLIC_IP
```

## Routine commands

```bash
cd /opt/monitoring
docker compose ps
./scripts/health-check.sh
docker compose logs --tail=200 prometheus
docker compose logs --tail=200 grafana
docker compose logs --tail=200 alertmanager
```

Use `docker compose restart SERVICE` for a controlled single-service restart. Use `docker compose up -d --build` after an approved configuration change.

## Target down

1. Open Prometheus **Status > Targets** through the SSH tunnel and identify the failing job and last error.
2. Confirm the target container is running with `docker compose ps`.
3. Review the target logs and Docker network membership.
4. If the exporter is healthy, inspect the relevant scrape URL from the Prometheus container.
5. Restart only the failing component. Escalate if the target remains down after one controlled restart.

## Endpoint down

1. Query `probe_success{instance="FAILED_URL"}` and inspect the Blackbox Exporter probe details.
2. Test the URL from inside the Docker network.
3. Confirm DNS, HTTP status, timeout, and health-route behavior.
4. Restore the endpoint, then verify `probe_success` returns to `1` and Alertmanager records a resolved alert.

## High CPU

1. Check the host utilization panel and `topk(8, sum by(name)(rate(container_cpu_usage_seconds_total{name!=""}[5m])))`.
2. Review the busiest container's logs and recent configuration or traffic changes.
3. Stop accidental load generation if present.
4. If sustained legitimate load exceeds capacity, increase the VM size during an approved maintenance window.

## High memory

1. Compare host memory utilization with per-container memory metrics in Prometheus Explore.
2. Check for restarts, out-of-memory events, or unbounded query/dashboard activity.
3. Reduce Prometheus retention only as a temporary documented mitigation if storage pressure is contributing.
4. Right-size the VM or separate services for recurring pressure.

## Low disk space

1. Run `df -h` and `docker system df`.
2. Identify log, image, and Prometheus growth. Do not delete persistent volumes.
3. Confirm Docker log rotation is active.
4. Remove only unused images after review, or increase the managed disk and filesystem.
5. Reassess the configured Prometheus retention period.

## Container pressure

1. Identify the container from the alert label and Grafana container panel.
2. Review logs, restart count, and recent changes.
3. Confirm the workload is not a planned load test.
4. Roll back the latest change or adjust capacity after approval.

## Application errors

1. Inspect the HTTP request-rate panel by status and query `demo:http_error_ratio:rate5m`.
2. Review `docker compose logs --tail=200 demo-app`.
3. Separate controlled `/simulate/error` traffic from unexpected failures.
4. Validate the health endpoint and one normal order request.

## Low inventory

The included alert demonstrates a business threshold. Restock the simulated service:

```bash
curl "http://127.0.0.1:8000/simulate/restock?quantity=100"
```

For a real application, the alert should link to the responsible inventory workflow rather than directly changing business data.

## No orders

This informational alert is expected in an idle demonstration. Generate one controlled order to validate the metric path:

```bash
curl "http://127.0.0.1:8000/simulate/order?amount=125&quantity=1"
```

In production, calibrate the time window against normal business hours and seasonality to avoid noisy alerts.

## Backup

```bash
cd /opt/monitoring
./scripts/backup.sh
ls -lh backups/
sha256sum -c backups/checksums-TIMESTAMP.sha256
```

Copy archives to encrypted off-VM storage. The local script backs up Prometheus, Alertmanager, and Grafana volumes; it does not back up Terraform state or Azure credentials.

## Upgrade

1. Read upstream release notes and compatibility guidance.
2. Create and verify a backup.
3. Update one image version in `.env` or `.env.example` through review.
4. Run `docker compose pull SERVICE` and `docker compose up -d SERVICE`.
5. Run the health check, inspect targets, dashboards, and firing alerts.
6. Roll back to the previous version if acceptance checks fail.

## Grafana password rotation

1. Stop Grafana.
2. Replace `secrets/grafana_admin_password.txt` with a newly generated value and mode `0600`.
3. Start Grafana and reset the administrator password using the supported Grafana CLI or user-administration workflow.
4. Store the new value in the approved secret manager and remove any temporary copies.

## Notification integration

The reference Alertmanager receiver posts to the demonstration application's `/alerts` endpoint. For production, configure an approved receiver (email, chat, or on-call), inject its credentials from a managed secret source, validate with a controlled alert, and keep the local webhook only if it remains useful for integration testing.
