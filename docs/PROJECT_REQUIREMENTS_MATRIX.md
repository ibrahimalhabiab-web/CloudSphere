# Project Requirements Traceability Matrix

This matrix maps the attached **Project #3: Internal Git and CI/CD Platform Based on GitLab** requirements to the combined implementation while retaining the Prometheus/Grafana observability project.

| Requirement | Implementation evidence | Status after authorized deployment |
|---|---|---|
| Azure infrastructure provisioning | `terraform/main.tf`, variables, outputs, and two cloud-init files | Implemented |
| VM hosting environment | Dedicated GitLab VM and monitoring/Runner VM | Implemented |
| Docker-based GitLab deployment | `gitlab/compose.yaml` with pinned GitLab CE image | Implemented |
| Persistent GitLab storage | `/srv/gitlab/config`, `/srv/gitlab/logs`, `/srv/gitlab/data` bind mounts | Implemented |
| Repository hosting/version control | Self-managed GitLab project workflow in `docs/GITLAB.md` | Requires live demonstration |
| Branch-based development | Protected `main`, feature branch, and merge-request workflow | Requires live demonstration |
| Commit history/change visibility | Internal repository push and merge-request evidence | Requires live demonstration |
| CI/CD pipeline execution | Root `.gitlab-ci.yml` and Runner service | Implemented; requires passing live pipeline |
| Code review/collaboration | Group, project, member, reviewer, and merge-request steps | Requires live demonstration |
| Basic deployment trigger | Protected manual `deploy_monitoring` job | Implemented; requires protected variables |
| Bash automation | Combined deploy, validate, health, Runner, backup, restore, and destroy scripts | Implemented |
| Docker Compose orchestration | Separate GitLab and monitoring Compose models | Implemented |
| GitLab health validation | Container health check plus `gitlab/scripts/health-check.sh` | Implemented |
| Backup/recovery guidance | GitLab application/config backup and guarded restore runbook | Implemented |
| Secure authentication/access | SSH keys, generated passwords, GitLab roles, restricted NSGs | Implemented for demo; production gaps documented |
| Restricted network exposure | Trusted CIDR validation and private monitoring paths | Implemented |
| CI/CD secret handling | `.gitignore`, protected variables, secret-detection job | Implemented |
| Operating-system hardening | Ubuntu updates, Secure Boot, vTPM, SSH-key authentication, log rotation | Implemented |
| Operational documentation | Architecture, GitLab guide, security review, runbook, test plan | Implemented |
| Enterprise software-delivery pattern | Source -> review -> CI -> manual CD -> monitoring -> alerts | Implemented as a reference pattern |

## Acceptance summary

The repository now contains every required implementation component. Final acceptance still requires authorized runtime evidence: Azure plan/apply, GitLab sign-in, repository push, merge request, Runner online state, passing pipeline, manual deployment, monitoring targets, dashboards, alerts, backups, and teardown.
