# Combined Platform Acceptance Test Plan

## Purpose

This plan verifies Azure provisioning, self-managed GitLab, repository collaboration, Runner execution, CI/CD, monitoring, alerting, persistence, security boundaries, backup, recovery safeguards, and teardown.

## Preconditions

- Azure permissions to create the declared resources.
- Sufficient regional vCPU quota for both selected VM SKUs.
- Terraform 1.8+, Azure CLI, Bash, OpenSSH, and `tar`.
- Trusted administrator public IPv4 `/32` and an SSH public key.
- A browser allowed by the restricted GitLab NSG plus the documented SSH tunnel to monitoring-VM loopback for Grafana.
- A GitLab runner authentication token for Runner tests.

## Static checks

```bash
chmod +x scripts/*.sh stack/scripts/*.sh gitlab/scripts/*.sh
./scripts/validate.sh
```

The GitLab pipeline must also pass its validation and unit-test stages.

## Infrastructure and deployment

| ID | Test | Procedure | Expected result |
|---|---|---|---|
| T01 | Terraform format/validation | Run `terraform init`, `terraform fmt -check -recursive`, and `terraform validate`. | Configuration initializes, formats, and validates. |
| T02 | Combined plan | Run `terraform plan`. | Plan includes one VNet, two subnets, two public IPs, two NSGs, two NICs, two VMs, disks, and optional schedules. |
| T03 | Restricted ingress | Inspect both NSGs. | No custom public inbound rule uses `0.0.0.0/0`; GitLab and monitoring access match trusted CIDRs. |
| T04 | Automated deployment | Run `./scripts/deploy-azure.sh`. | Both VMs bootstrap; GitLab and monitoring health checks pass. |
| T05 | Persistence paths | Inspect `/srv/gitlab` and Docker volumes. | GitLab config/log/data paths and monitoring volumes exist without secrets in Git. |

## GitLab and collaboration

| ID | Test | Procedure | Expected result |
|---|---|---|---|
| T06 | GitLab health | Open GitLab and run `gitlab/scripts/health-check.sh`. | Sign-in page loads and `/-/health` returns `GitLab OK`. |
| T07 | Repository hosting | Create a group/project and push `main`. | Files and commit history appear in self-managed GitLab. |
| T08 | Branch workflow | Push a feature branch and open a merge request. | Diff, commits, reviewer controls, and pipeline status are visible. |
| T09 | Runner registration | Register with `register-runner.sh`. | Runner appears online and can execute Docker jobs. |
| T10 | CI validation | Run a merge-request pipeline. | Terraform, ShellCheck, Python/dashboard, Compose, unit-test, and secret jobs complete as configured. |
| T11 | Controlled failure | Introduce a temporary test-only syntax error on a branch. | The relevant job fails and the merge request shows the failure; reverting it restores a passing pipeline. |
| T12 | Manual deployment | Configure protected variables and run `deploy_monitoring` from `main`. | Monitoring stack updates and health checks pass. |

## Monitoring and observability

| ID | Test | Procedure | Expected result |
|---|---|---|---|
| T13 | Container state | Run Compose `ps` on both VMs. | GitLab is healthy; monitoring services and Runner are running. |
| T14 | Prometheus targets | Open **Status > Targets**. | Core, GitLab application, GitLab host, GitLab health, Runner, exporter, and application targets are up. |
| T15 | Dashboard provisioning | Open Grafana. | CloudSphere Infrastructure Command Center and CloudSphere GitLab Control Plane dashboards exist without manual import. |
| T16 | GitLab metrics | Query `up{job="gitlab"}` and `scrape_samples_scraped{job="gitlab"}`. | GitLab is `1` and returns non-zero samples. |
| T17 | GitLab probe | Query `probe_success{job="gitlab-health"}`. | Independent GitLab health probe returns `1`. |
| T18 | Runner and GitLab host metrics | Query `up{job="gitlab-runner"}` and `up{job="gitlab-node"}`. | Both metrics targets return `1`. |
| T19 | Host/container telemetry | Inspect CPU, memory, disk, and container panels. | Current non-empty values appear for both Linux hosts and monitoring containers. |
| T20 | Business activity | Submit order, restock, and error requests. | Orders, revenue, inventory, and errors change after scraping. |
| T21 | CloudSphere reset | POST to `/simulate/reset`. | Orders, revenue, errors, and inventory return to the documented initial state after scraping. |
| T22 | Alert lifecycle | Stop GitLab or Runner in a controlled window, wait for the rule, then restart. | Alert becomes pending/firing, reaches Alertmanager, and resolves after recovery. |

## Security, persistence, and recovery

| ID | Test | Procedure | Expected result |
|---|---|---|---|
| T23 | Private interfaces | Attempt public connections to 9090, 9093, 8000, and exporter ports. | Connections are blocked; approved tunnels/private paths work. |
| T24 | Password handling | Run `git status` after deployment preparation. | Generated GitLab/Grafana password files remain ignored. |
| T25 | Restart persistence | Stop/start both Compose projects without removing data. | Repository, users, pipeline records, dashboards, and metric history persist. |
| T26 | GitLab backup | Run `gitlab/scripts/backup.sh`. | Application archive, configuration archive, and checksum file are created. |
| T27 | Monitoring backup | Run `stack/scripts/backup.sh`. | Three monitoring archives and checksum file are created. |
| T28 | Restore safeguard | Run GitLab restore without confirmation. | Script exits without changing data and prints the required confirmation. |
| T29 | Teardown safeguard | Run Azure destroy without confirmation. | Script exits without changing infrastructure. |
| T30 | Auto-shutdown | Inspect schedules when enabled. | Both VMs have the configured daily schedule. |

## Acceptance criteria

- T01-T10 and T13-T21 pass.
- T22 is exercised in a controlled maintenance window.
- T23-T30 pass or have an explicit documented exception and owner.
- A merge request shows both collaboration and a passing pipeline.
- The protected manual deployment runs only from the default branch.
- No live password, token, private key, state, plan, or webhook credential exists in the submitted repository.
- No custom public inbound rule uses `0.0.0.0/0`.
- Both dashboards show current data and GitLab monitoring jobs are healthy.

## Evidence checklist

Capture non-sensitive evidence only:

- Terraform plan summary and Azure resource list
- Both NSG rule tables
- GitLab sign-in and project page without credentials
- Repository branch, merge request, and commit history
- Passing pipeline job list
- Both Compose `ps` outputs
- Prometheus targets and GitLab queries
- Both Grafana dashboards
- Firing and resolved GitLab/Runner test alert
- Backup archive names and checksum verification
- Safe destroy prompt and final destroy completion when authorized

Redact subscription IDs, public addresses, usernames, email addresses, tokens, passwords, SSH material, and private repository content before sharing evidence.
