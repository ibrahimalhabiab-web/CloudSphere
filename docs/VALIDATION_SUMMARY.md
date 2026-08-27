# Validation Summary

Validation date: 26 August 2026

## Passed in the build workspace

| Check | Result | Scope |
|---|---|---|
| Terraform formatting | PASS | All active Terraform files with Terraform 1.15.8 |
| Terraform initialization and validation | PASS | Isolated provider-backed validation with AzureRM 4.81.0 |
| Provider integrity | PASS | Windows AzureRM 4.81.0 archive matched HashiCorp's published SHA-256 value |
| Demo application syntax | PASS | Python byte-code compilation |
| Demo application unit tests | PASS | Three tests covering metric escaping, required business metrics, and reset behavior |
| ShellCheck 0.10 and Bash syntax | PASS | All 13 Bash deployment, lifecycle, health, Runner, backup, and restore scripts |
| YAML parsing | PASS | 15 CI, Compose, cloud-init, Prometheus, Alertmanager, Blackbox, and provisioning files; duplicate keys rejected |
| JSON parsing | PASS | Both Grafana dashboard definitions |
| Configuration assertions | PASS | Expected Compose services, GitLab monitoring jobs, restricted Terraform access, and secret exclusions |
| Documentation links | PASS | All 12 relative links across 12 Markdown files resolve |
| Final report structure | PASS | Valid OOXML package, 145 paragraphs, seven fixed-geometry data tables, real headings/lists, and one consistent Letter section |
| Final report accessibility | PASS | Zero high-, medium-, or low-severity findings from the DOCX accessibility audit |
| Git patch hygiene | PASS | No whitespace errors reported by `git diff --check` |

The tracked Terraform dependency lock selects AzureRM 4.81.0. Runtime passwords, `.env` files, state, plans, private keys, Runner tokens, and GitLab backup archives are excluded from version control and from the delivery archive.

## Validated by the GitLab pipeline

The root `.gitlab-ci.yml` repeats the main checks in clean Linux containers. It additionally runs both full Docker Compose model validations and GitLab secret detection. A passing pipeline on the self-managed GitLab instance is required final evidence because this Windows build workspace does not provide Docker Engine.

The final Word report could not be rendered to page images in this workspace because LibreOffice is not installed and Microsoft Word cannot open from the background execution session. It passed package integrity, style, section, heading, table-geometry, hyperlink, and accessibility audits. Open it once in Microsoft Word and review pagination before institutional submission.

## Requires the authorized Azure environment

The following checks require the user's Azure subscription, trusted network, live VMs, and GitLab account and are therefore not claimed as completed in this build workspace:

- `terraform plan`, approved `apply`, and final `destroy` against the selected Azure subscription.
- Both Compose stacks starting successfully on Ubuntu and surviving a stop/start cycle.
- Initial GitLab sign-in, password rotation, group/project creation, member roles, protected `main`, and a reviewed merge request.
- Project Runner registration, online status, repository cloning over the private VNet, and a passing pipeline.
- Protected manual deployment with verified SSH host keys and masked CI/CD variables.
- Prometheus GitLab, GitLab host, Runner, health, application, host, container, and blackbox targets reporting `UP`.
- Live Grafana dashboards, firing/resolved alerts, backup checksum verification, guarded restore rehearsal, and persistence after restart.

Run `scripts/validate.sh`, then follow `docs/TEST_PLAN.md` and `docs/DEMO_GUIDE.md` on the authorized environment. Capture non-sensitive screenshots and redact passwords, tokens, SSH keys, subscription identifiers, and public IP addresses.
