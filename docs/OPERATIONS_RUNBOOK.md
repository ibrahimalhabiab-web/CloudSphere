# Combined Platform Operations Runbook

## 1. Identify the hosts

```bash
terraform -chdir=terraform output
```

This displays both public addresses, GitLab's private monitoring address, service URLs, and SSH commands. Do not publish live output without redacting addresses, subscription identifiers, and usernames.

## 2. Routine status

### GitLab VM

```bash
ssh azureadmin@GITLAB_PUBLIC_IP
cd /opt/gitlab-stack
docker compose --env-file .env ps
./scripts/health-check.sh
docker compose --env-file .env logs --tail=200 gitlab
```

### Monitoring VM

```bash
ssh azureadmin@MONITORING_PUBLIC_IP
cd /opt/monitoring
docker compose --env-file .env ps
./scripts/health-check.sh
docker compose --env-file .env logs --tail=200 prometheus
docker compose --env-file .env logs --tail=200 grafana
docker compose --env-file .env logs --tail=200 gitlab-runner
```

When the optional public status page is enabled, use the DNS, HTTPS, route-isolation, troubleshooting, and rollback checks in [PUBLIC_ACCESS.md](PUBLIC_ACCESS.md). Its public availability also depends on the monitoring VM being powered on.

## 3. Stop and reopen

Use `stop` to preserve containers and all persistent data:

```bash
# GitLab VM
cd /opt/gitlab-stack
docker compose --env-file .env stop

# Monitoring VM
cd /opt/monitoring
docker compose --env-file .env stop
```

Reopen:

```bash
# GitLab VM
cd /opt/gitlab-stack
docker compose --env-file .env start
./scripts/health-check.sh --wait

# Monitoring VM
cd /opt/monitoring
docker compose --env-file .env start
./scripts/health-check.sh
```

If Azure auto-shutdown stopped the VMs, start the GitLab VM first, then the monitoring VM. Docker restart policies should start services automatically. Run both health checks after SSH becomes available.

## 4. GitLab unavailable

1. Check Azure VM state and GitLab NSG rules.
2. SSH to the GitLab VM and run `docker compose ps`.
3. Test locally with `curl -fsS http://127.0.0.1/-/health`.
4. Review GitLab logs: `docker compose logs --tail=300 gitlab`.
5. Check disk and memory: `df -h`, `free -h`, and `docker stats --no-stream`.
6. Inspect internal services: `docker compose exec -T gitlab gitlab-ctl status`.
7. Perform one controlled restart: `docker compose restart gitlab`.
8. Wait with `./scripts/health-check.sh --wait`.
9. If the local check passes but the browser fails, inspect trusted CIDRs, the external URL, and public-IP changes.

Do not delete `/srv/gitlab` or run `docker compose down -v` during diagnosis.

## 5. Runner unavailable

```bash
cd /opt/monitoring
docker compose --env-file .env ps gitlab-runner
docker compose --env-file .env logs --tail=200 gitlab-runner
docker compose --env-file .env exec -T gitlab-runner gitlab-runner list
```

Confirm:

- The Runner appears online in GitLab.
- The monitoring VM can reach `GITLAB_URL`.
- The Runner authentication token is still active.
- The Docker socket exists and Docker is running.
- GitLab and Runner versions remain compatible.

Restart only Runner after review:

```bash
docker compose --env-file .env restart gitlab-runner
```

## 6. Prometheus target or endpoint down

1. Open Prometheus **Status > Targets** through the SSH tunnel.
2. Identify the failing `job` and `instance`.
3. For GitLab, confirm the `gitlab`, `gitlab-node`, and `gitlab-health` jobs.
4. Test private connectivity from the monitoring VM:

   ```bash
   curl -fsS http://GITLAB_PRIVATE_IP/-/health
   curl -fsS http://GITLAB_PRIVATE_IP/-/metrics | head
   curl -fsS http://GITLAB_PRIVATE_IP:9100/metrics | head
   ```

5. Confirm generated targets:

   ```bash
   cat /opt/monitoring/prometheus/file_sd/gitlab-metrics.yml
   cat /opt/monitoring/prometheus/file_sd/gitlab-node.yml
   cat /opt/monitoring/prometheus/file_sd/gitlab-health.yml
   ```

6. Check the relevant service logs and restore the target.
7. Verify `up` or `probe_success` returns to `1` and Alertmanager receives the resolved alert.

## 7. Host or container pressure

1. Review the Grafana host and container panels.
2. Run `top`, `free -h`, `df -h`, `docker system df`, and `docker stats --no-stream`.
3. Identify planned pipeline load versus unexpected resource consumption.
4. Stop accidental test traffic or a stuck pipeline.
5. Remove only reviewed, unused images; never delete persistent volumes as a space-recovery shortcut.
6. Resize the affected VM during an approved maintenance window when pressure is recurring.

## 8. CloudSphere application and dashboard reset

Use the browser-based CloudSphere Operations Console for a presentation:

```text
http://127.0.0.1:8000
```

Select **Generate 3 orders** for business activity, **Trigger alert sequence** for the controlled high-error sequence, **Run 30-second server load** for bounded CPU pressure, and **Reset all metrics** for recovery. The page polls its own current state and opens Grafana with a fifteen-minute range and two-second refresh.

If the browser controls are unavailable, use these operator fallback endpoints:

```bash
curl "http://127.0.0.1:8000/simulate/order?amount=125.50&quantity=2"
curl "http://127.0.0.1:8000/simulate/restock?quantity=50"
curl -i "http://127.0.0.1:8000/simulate/error"
curl -X POST -H "X-CloudSphere-Control: 1" http://127.0.0.1:8000/simulate/load/start
curl -X POST -H "X-CloudSphere-Control: 1" http://127.0.0.1:8000/simulate/load/stop
```

Reset the in-memory CloudSphere values:

```bash
curl -X POST http://127.0.0.1:8000/simulate/reset
```

Wait for one or two two-second Prometheus scrape intervals and one Grafana refresh. The high-error rule uses a ten-second rate window, so allow approximately 10–15 seconds after reset for it to return to `INACTIVE`. Historical samples remain visible; use the CloudSphere Grafana shortcut to stay on the live fifteen-minute view.

## 9. Monitoring backup

```bash
cd /opt/monitoring
./scripts/backup.sh
ls -lh backups/
sha256sum -c backups/checksums-TIMESTAMP.sha256
```

The script archives Prometheus, Alertmanager, and Grafana volumes. Back up the Runner configuration separately only if required by policy; Runner can normally be re-registered.

## 10. GitLab backup

```bash
cd /opt/gitlab-stack
./scripts/backup.sh
ls -lh backups/
sha256sum -c backups/checksums-TIMESTAMP.sha256
```

This creates a GitLab application backup plus a separate configuration/secrets archive. Copy both and their checksums to encrypted off-VM storage. A GitLab application archive without the matching secrets/configuration archive is insufficient for complete recovery.

## 11. GitLab restore

Restore is destructive and requires:

- A clean, working destination GitLab installation.
- The exact same GitLab version and edition as the backup.
- The application archive in `/srv/gitlab/data/backups`.
- The matching configuration and secrets restored first.
- A verified maintenance window and rollback plan.

After preparing these prerequisites:

```bash
cd /opt/gitlab-stack
CONFIRM_RESTORE=yes BACKUP_ID=TIMESTAMP_VERSION ./scripts/restore.sh
```

The script stops application processes, restores, restarts GitLab, and runs a sanitized GitLab check. Test restoration regularly on an isolated recovery instance.

## 12. Upgrade

1. Read GitLab, Runner, Prometheus, Grafana, and exporter release notes.
2. Verify supported upgrade paths, especially for GitLab.
3. Create and copy backups off both VMs.
4. Update exactly one pinned image version through a merge request.
5. Run the complete pipeline and Compose validation.
6. Pull and restart only the affected service.
7. Run health checks, Prometheus targets, dashboards, and a controlled pipeline.
8. Roll back to the previous compatible version if acceptance checks fail.

Never skip required GitLab upgrade stops between major or minor versions.

## 13. Safe teardown

```bash
./scripts/destroy-azure.sh
CONFIRM_DESTROY=yes ./scripts/destroy-azure.sh
```

The first command changes nothing and prints the required confirmation. Before confirmed destruction, copy GitLab and monitoring backups off the VMs and verify the destination files.
