# Acceptance Test Plan

## Purpose

This plan verifies that infrastructure provisioning, deployment automation, metric collection, visualization, alerting, persistence, security boundaries, and teardown behave as designed.

## Preconditions

- An Azure subscription and permission to create the declared resources.
- Terraform 1.8+, Azure CLI, Bash, OpenSSH, and `tar`.
- A trusted administrator public IPv4 `/32` and an SSH public key.
- For a local test: Linux with Docker Engine and Compose v2.

## Static checks

Run from the project root:

```bash
chmod +x scripts/*.sh stack/scripts/*.sh
./scripts/validate.sh
```

Record the final pass/fail line and any skipped checks.

## Deployment and functional tests

| ID | Test | Procedure | Expected result |
|---|---|---|---|
| T01 | Terraform validation | Run `terraform init`, `terraform fmt -check -recursive`, and `terraform validate`. | Configuration initializes, is formatted, and validates without errors. |
| T02 | Infrastructure plan | Run `terraform plan`. | Plan contains the resource group, VNet, subnet, IP, NSG, NIC, VM, and optional shutdown schedule; no unexpected resources appear. |
| T03 | Restricted ingress | Inspect the NSG after apply. | SSH and Grafana sources equal the configured trusted CIDR; Prometheus has no public rule when `expose_prometheus=false`. |
| T04 | Automated deployment | Run `./scripts/deploy-azure.sh`. | Script waits for bootstrap, uploads the stack, starts services, and finishes with passing health checks. |
| T05 | Container state | Run `docker compose ps` on the VM. | All seven services are running; Grafana and demo-app report healthy after startup. |
| T06 | Prometheus targets | Open Prometheus **Status > Targets** via SSH tunnel. | Prometheus, node, containers, demo-application, blackbox-exporter, and service-uptime jobs are up. |
| T07 | Grafana provisioning | Sign in and open the dashboard. | Prometheus exists as the default data source and the Operations Overview dashboard is present without manual import. |
| T08 | Host telemetry | Observe CPU, memory, and root disk panels. | Panels return non-empty current values from Node Exporter. |
| T09 | Container telemetry | Observe the container CPU panel. | Running platform containers appear with current cAdvisor samples. |
| T10 | Endpoint monitoring | Query `probe_success`. | Four monitored internal endpoints return `1`. |
| T11 | Business metrics | Submit an order and restock request. | Orders and revenue increase; inventory decreases and then increases on the dashboard. |
| T12 | Error telemetry | Send repeated `/simulate/error` requests. | HTTP 500 request series increases; the error-ratio query becomes non-zero. |
| T13 | Alert delivery | Temporarily stop `demo-app` long enough for an availability rule to fire, then restart it. | Prometheus shows pending/firing state, Alertmanager receives the alert, and the alert later resolves. |
| T14 | Persistence | Restart the Compose project without deleting volumes. | Dashboard configuration/data and Prometheus history remain available. |
| T15 | Backup | Run `stack/scripts/backup.sh`. | Three timestamped archives and one checksum file are created and the checksum verifies. |
| T16 | Private interfaces | Attempt public connections to ports 9090, 9093, and 8000. | Connections are blocked; the same interfaces work through localhost or SSH tunneling as designed. |
| T17 | Auto-shutdown | Inspect the Azure schedule when enabled. | A daily shutdown schedule exists with the configured time zone and time. |
| T18 | Teardown safety | Run `scripts/destroy-azure.sh` without confirmation, then with `CONFIRM_DESTROY=yes`. | First run changes nothing; confirmed run presents the Terraform destroy workflow. |

## Demonstration commands

```bash
curl "http://127.0.0.1:8000/simulate/order?amount=125.50&quantity=2"
curl "http://127.0.0.1:8000/simulate/restock?quantity=50"
for i in $(seq 1 20); do curl -s -o /dev/null "http://127.0.0.1:8000/simulate/error"; done
```

## Acceptance criteria

- All mandatory tests T01-T12 and T16 pass.
- Alert delivery T13 is demonstrated in a controlled window.
- No password, private key, Terraform state, or live webhook credential exists in the submitted repository.
- The Grafana dashboard contains current host, container, endpoint, application, and business information.
- No public inbound rule uses `0.0.0.0/0`.
- Any skipped test has a documented reason and follow-up owner.

## Evidence checklist

Capture only non-sensitive evidence: Terraform plan summary, Azure resource list, NSG rule table, `docker compose ps`, Prometheus targets, the Grafana dashboard, a firing/resolved test alert, backup file list, and Terraform destroy completion. Redact subscription IDs, public IPs, user identities, and secrets before sharing screenshots.
