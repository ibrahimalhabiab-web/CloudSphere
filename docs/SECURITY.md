# Security Review

## Security objectives

- Keep GitLab and monitoring administration limited to explicitly trusted networks.
- Prevent passwords, runner tokens, cloud credentials, state, and SSH private keys from entering source control.
- Separate source-control services from CI execution and monitoring workloads.
- Require review and explicit approval for deployments and destructive operations.
- Preserve a version-controlled audit trail for infrastructure, configuration, dashboards, rules, and automation.

## Implemented controls

| Area | Control |
|---|---|
| Azure ingress | Separate NSGs protect each VM. Terraform rejects `0.0.0.0/0`; GitLab access defaults to the administrator CIDR. |
| Linux access | SSH keys only; password authentication is disabled, Secure Boot and vTPM are enabled, and platform patching is configured. |
| GitLab web and Git SSH | Restricted to trusted CIDRs on ports 80/443 and 2222. Host administration remains separate on port 22. |
| GitLab credentials | Initial root password is generated on the GitLab host with restrictive permissions and ignored by Git. |
| GitLab metrics | Monitoring allowlist permits only loopback and the private Azure VNet. Bundled Prometheus is disabled, and the separate GitLab host exporter has no public NSG rule. |
| Grafana | Anonymous access and public signup are disabled; the admin password is generated as a Compose secret. |
| Monitoring interfaces | Prometheus, Alertmanager, and the demo application bind to host loopback. Exporters remain on the Docker network. |
| CI Runner | Runner is deployed away from the GitLab application. Registration tokens and deployment keys are not stored in the repository. |
| CI deployment | Deployment is manual, limited to the default branch, and uses protected CI/CD variables plus a pre-verified SSH known-hosts entry. Terraform apply/destroy are not automated. |
| Secret scanning | GitLab's maintained secret-detection template is included in the pipeline. |
| Container lifecycle | Persistent volumes, health checks, restart policies, log rotation, and `no-new-privileges` are used where compatible. |
| Recovery safety | GitLab restore and Terraform destroy require explicit confirmation. |
| Cost control | Both VMs can use an optional daily auto-shutdown schedule. |

## Important residual risks

1. **Training HTTP endpoints:** GitLab and Grafana use restricted HTTP for a simple demonstration. Add DNS, trusted TLS certificates, secure redirects, and secure cookies before production.
2. **Constrained GitLab sizing:** The example GitLab VM is smaller than the current normal single-node baseline. Slow response, initialization delay, or resource exhaustion is possible.
3. **Single-node services:** Each VM is a failure domain. There is no GitLab, Prometheus, Grafana, or Alertmanager high availability.
4. **Docker socket:** Runner requires access to the Docker socket to create Docker executor jobs. Compromise of a CI job or Runner can lead to host-level control. Use dedicated ephemeral Runner hosts and tightly governed projects in production.
5. **Privileged cAdvisor:** Container telemetry requires privileged access and host mounts. Isolate or replace it in higher-assurance environments.
6. **Local secrets:** Password files are protected and ignored but still reside on VM disks. Move them to Azure Key Vault or another managed secret service.
7. **Local Terraform state:** The reference project does not configure a remote backend by default. Use encrypted, access-controlled remote state with locking and auditing.
8. **Local backups:** Backup scripts create VM-local archives. VM loss also loses those archives unless they are copied to encrypted off-VM storage.
9. **Mutable image tags:** Versions are pinned, but tags are not content-addressable. Validate and pin trusted image digests for production.
10. **Open egress:** Both VMs use normal outbound access for packages and images. Apply egress controls and approved registries in production.
11. **No organizational identity:** Local GitLab and Grafana accounts are suitable only for training. Add SSO, MFA, role governance, and access reviews.
12. **CI key scope:** A deployment private key can modify the monitoring host. Use a dedicated account and command restrictions where possible.
13. **Host-key lifecycle:** CI pins the monitoring VM's SSH host key. A legitimate VM rebuild requires controlled fingerprint verification and variable rotation before deployment resumes.

## Secret inventory

Never commit or paste these values into screenshots:

- `terraform/terraform.tfvars`
- Terraform state, plan files, or backend credentials
- Azure service-principal credentials
- GitLab root password
- GitLab runner authentication tokens (`glrt-...`)
- GitLab personal/project access tokens
- Grafana admin password
- CI deployment private key
- SSH private keys
- Live notification webhook URLs or credentials

The `.gitignore` covers expected local secret and state files. GitLab secret detection provides another control, but it is not a substitute for disciplined handling and credential rotation.

## Pre-production gate

- DNS and TLS configured for GitLab and Grafana.
- GitLab sizing validated against current requirements and measured workload.
- Administrator and team CIDRs reviewed.
- Organizational SSO, MFA, roles, and protected branches configured.
- Secrets migrated to a managed store and rotation tested.
- Runner isolated, scoped, patched, and monitored.
- CI deployment host key independently verified and rotation procedure tested.
- Images scanned, signed where appropriate, and digest-pinned.
- Remote Terraform state and backup storage access audited.
- GitLab application plus configuration backups copied off VM.
- Exact-version restore rehearsed.
- Alert receivers and escalation ownership tested.
- Recovery objectives and capacity thresholds approved.
