# Security Review

## Security objectives

- Prevent unauthenticated public access to administrative services.
- Avoid passwords and cloud credentials in source control.
- Minimize container privileges and writable filesystems.
- Preserve a clear audit trail through infrastructure and configuration as code.
- Make destructive and cost-generating operations explicit.

## Implemented controls

| Area | Control |
|---|---|
| Azure ingress | NSG rules limit SSH and Grafana to a required trusted CIDR. `0.0.0.0/0` is rejected by Terraform validation. |
| VM authentication | Password login is disabled; the VM accepts the configured SSH public key. |
| Monitoring interfaces | Prometheus, Alertmanager, and the demo service bind to `127.0.0.1` on the host. Exporter ports remain on the Docker network. |
| Grafana | Anonymous access and public signup are disabled; the administrator password is generated at deployment time. |
| Secrets | The password is mounted as a Compose secret and ignored by Git. No Azure credential is stored in the project. |
| Container hardening | Services use read-only configuration mounts, persistent data volumes, restart policies, and `no-new-privileges` where compatible. |
| Host maintenance | Cloud-init enables unattended Ubuntu upgrades and Docker log rotation. |
| Cost control | Optional daily VM shutdown is enabled by default; teardown requires a deliberate confirmation variable. |

## Residual risks and production actions

1. **Transport security:** the reference Grafana endpoint uses restricted HTTP. Put Grafana behind TLS before production and set secure cookie options.
2. **Identity:** replace local Grafana administration with organizational single sign-on, role mapping, and least-privilege teams.
3. **Secret lifecycle:** use Azure Key Vault or another managed secret store and establish password rotation.
4. **Privileged collector:** cAdvisor requires privileged host visibility. Isolate the collector, monitor its image, and consider a node-level agent architecture for higher assurance.
5. **Image integrity:** pinned versions reduce drift, but production should also pin image digests and run vulnerability/signature checks in CI.
6. **State protection:** use encrypted, access-controlled remote Terraform state with locking and audit logs.
7. **Availability:** a single VM is a single failure domain. Use redundant instances and an external durable metric store when availability objectives demand it.
8. **Backups:** the included backup is local to the VM. Encrypt and copy backups off the VM, apply retention, and test restoration.
9. **Egress:** the reference network permits normal outbound traffic for package and image downloads. Production should apply egress controls and use trusted registries.
10. **Notification privacy:** configure approved email, chat, or on-call receivers; do not place webhook tokens directly in committed Alertmanager files.

## Pre-production gate

- TLS certificate deployed and renewal tested.
- Single sign-on and role assignments reviewed.
- Trusted administrator CIDRs confirmed.
- Secrets migrated to a managed store.
- Container images scanned and digest-pinned.
- Remote state and backup access audited.
- Alert receivers tested with a controlled notification.
- Recovery and rollback rehearsed.
- Resource sizing and retention validated under representative load.
