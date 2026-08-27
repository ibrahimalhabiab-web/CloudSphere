# Guided Demonstration

## Before the audience arrives

1. Start both Azure VMs, GitLab first.
2. Run GitLab and monitoring health checks.
3. Confirm the Runner is online.
4. Confirm the latest `main` pipeline passed.
5. Open GitLab, Prometheus targets, both Grafana dashboards, and Alertmanager through approved access paths.
6. Reset the demo application with `curl -X POST http://127.0.0.1:8000/simulate/reset`.
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
9. **Show dashboards:** open Operations Overview and GitLab Platform Health.
10. **Generate activity:** create an order and error, then wait for panels to refresh.
11. **Show alerting:** use a controlled service stop only if the presentation window allows the alert duration.
12. **Recover:** restart the service and show the resolved state.
13. **Reset:** return demonstration values to the initial state.
14. **Close:** explain backups, security controls, production gaps, and safe teardown.

## Commands used during the demonstration

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
