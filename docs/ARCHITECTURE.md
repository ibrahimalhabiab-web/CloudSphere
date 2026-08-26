# Architecture Design

## 1. Design goal

The platform provides one operational view of host health, container health, service uptime, application behavior, and selected business metrics. The reference architecture emphasizes repeatability, low demonstration cost, and clear security boundaries while remaining small enough to deploy from a student or proof-of-concept Azure subscription.

## 2. Architecture decisions

| Decision | Implementation | Rationale |
|---|---|---|
| Deployment model | One Ubuntu 24.04 LTS Azure VM | Keeps the reference environment understandable and economical. |
| Infrastructure management | Terraform with AzureRM provider | Produces a repeatable plan and auditable desired state. |
| Application packaging | Docker Compose | Defines services, volumes, networks, and restart behavior in one version-controlled model. |
| Metric storage | Prometheus local persistent volume | Supports the required PromQL, rule, and dashboard workflow without an external dependency. |
| Visualization | Grafana provisioned from files | Eliminates manual data-source and dashboard setup. |
| Host telemetry | Node Exporter | Supplies CPU, memory, disk, and operating-system metrics. |
| Container telemetry | cAdvisor | Supplies per-container CPU, memory, filesystem, and network metrics. |
| Availability | Blackbox Exporter | Probes important HTTP health endpoints independently of their own metrics. |
| Notifications | Alertmanager to demonstration webhook | Proves routing, grouping, inhibition, and delivery without requiring private organizational credentials. |
| Secrets | Compose secret file generated with OpenSSL | Prevents a default Grafana password from being stored in the repository. |

## 3. Data flow

1. Exporters and the demonstration application expose Prometheus-format metrics on the private Docker network.
2. Prometheus scrapes every target at 15-second intervals and writes samples to its persistent volume.
3. Recording rules precompute host utilization and application error ratios for efficient dashboard queries.
4. Alerting rules evaluate every 15 seconds. Pending conditions become firing alerts only after their specified duration.
5. Prometheus forwards firing and resolved alerts to Alertmanager.
6. Alertmanager groups, inhibits, and sends notifications to the demonstration webhook endpoint.
7. Grafana queries Prometheus through the private Docker network and renders the provisioned operations dashboard.

## 4. Network boundaries

| Path | Exposure | Control |
|---|---|---|
| SSH, TCP 22 | Public IP | Azure NSG permits only `admin_source_cidr`. |
| Grafana, TCP 3000 | Public IP | Azure NSG permits only `admin_source_cidr`; authentication is mandatory. |
| Prometheus, TCP 9090 | VM loopback | Use SSH port forwarding; optional public exposure is disabled by default. |
| Alertmanager, TCP 9093 | VM loopback | Use SSH port forwarding when administrative access is needed. |
| Demo application, TCP 8000 | VM loopback | Used only for local demonstration traffic and alert delivery. |
| Exporter ports | Docker bridge only | No host publishing or Azure inbound rule. |

## 5. Persistence and recovery

Prometheus, Grafana, and Alertmanager each use an explicitly named Docker volume. The backup script creates timestamped compressed archives plus SHA-256 checksums. These archives remain on the VM in the reference build; production requires scheduled transfer to encrypted off-VM storage and periodic restore testing.

## 6. Security model

The design uses SSH keys only, rejects an open administrator CIDR, keeps non-user interfaces private, disables anonymous Grafana access, generates a high-entropy password, applies `no-new-privileges` where compatible, enables Ubuntu unattended upgrades, and rotates Docker logs. cAdvisor is the exception: host-level container telemetry requires privileged access and read-only host mounts. That risk is documented and should be isolated or replaced in higher-assurance environments.

## 7. Scalability and production evolution

The single VM is deliberately not highly available. A production architecture should separate ingestion, storage, visualization, and notification concerns; add redundant Prometheus replicas or a scalable long-term store; deploy Grafana behind TLS and single sign-on; place interfaces behind private networking or a controlled application gateway; store secrets in Azure Key Vault; protect Terraform state remotely; and ship backups outside the VM. Capacity decisions should be based on measured active-series count, scrape frequency, retention, dashboard concurrency, and recovery objectives.
