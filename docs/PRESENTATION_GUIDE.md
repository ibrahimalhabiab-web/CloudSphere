# Guided Presentation

## Before the audience arrives

1. Start both Azure VMs, GitLab first.
2. Run GitLab and monitoring health checks.
3. Confirm the Runner is online.
4. Confirm the latest `main` pipeline passed.
5. Open CloudSphere Operations Console at `http://127.0.0.1:8000`, GitLab, Prometheus Alerts, both Grafana dashboards, and Alertmanager through approved access paths.
6. Select **Reset all metrics** in CloudSphere Operations Console.
7. Use a browser window that does not expose passwords, tokens, public IPs, or unrelated accounts.

## Presentation sequence

1. **Explain the problem:** disconnected source control, manual releases, and separate monitoring slow delivery and troubleshooting.
2. **Show Terraform:** identify the VNet, two subnets, two NSGs, two VMs, disks, and schedules.
3. **Show GitLab:** open the internal project, repository tree, commit history, and protected default branch.
4. **Show collaboration:** open a feature-branch merge request and its review controls.
5. **Show CI:** open the pipeline and explain Terraform, ShellCheck, Python/dashboard, Compose, unit-test, and secret jobs.
6. **Show CD:** explain the protected manual deployment job and why infrastructure apply remains operator approved.
7. **Show runtime:** display Compose `ps` on both VMs.
8. **Show targets:** display GitLab, GitLab health, Runner, host, container, and application Prometheus jobs.
9. **Show dashboards:** place CloudSphere Operations Console and the CloudSphere Infrastructure Command Center side by side, then briefly open the CloudSphere GitLab Control Plane.
10. **Generate business activity:** select **Generate 3 orders** and show the order, revenue, and inventory counters in CloudSphere while Grafana remains focused on server and container health.
11. **Show application alerting:** select **Trigger alert sequence** and show `CloudSphereApplicationHighErrorRate` progress from `INACTIVE` to `PENDING` to `FIRING` in Prometheus and Grafana.
12. **Show infrastructure pressure:** open Grafana from the CloudSphere shortcut, select **Run 30-second server load**, and show the CloudSphere container CPU, host CPU, load average, and `CloudSphereControlledCpuLoad` alert react.
13. **Recover:** let the CPU test stop automatically or select **Stop & recover**, then select **Reset all metrics** and allow the short rate windows to clear.
14. **Close:** explain backups, security controls, production gaps, and safe teardown.

## Browser controls used during the presentation

| Action | CloudSphere control | Expected result |
|---|---|---|
| Start clean | **Reset all metrics** | Orders 0, revenue 0, inventory 100, errors 0 |
| Generate activity | **Generate 3 orders** | Orders 3, revenue 450, inventory 96 |
| Test a single failure | **Send one test error** | Error counter increases by one |
| Trigger the app alert | **Trigger alert sequence** | 20 HTTP 500 responses over about eight seconds; alert appears pending, then firing |
| Trigger infrastructure pressure | **Run 30-second server load** | Real capped CPU activity appears in cAdvisor, Prometheus, and Grafana |
| Recover | **Stop & recover** or **Reset all metrics** | CPU load stops; short rate windows drain back to baseline |

The following commands are retained only as a troubleshooting fallback:

```bash
# Monitoring health and services
cd /opt/monitoring
./scripts/health-check.sh
docker compose --env-file .env ps

# Generate business activity
curl "http://127.0.0.1:8000/simulate/order?amount=125.50&quantity=2"
curl -i "http://127.0.0.1:8000/simulate/error"

# Reset business values
curl -X POST http://127.0.0.1:8000/simulate/reset
```

```bash
# GitLab health and services
cd /opt/gitlab-stack
./scripts/health-check.sh
docker compose --env-file .env ps
```

Never run restore, destroy, token display, or password display commands in front of an audience.
