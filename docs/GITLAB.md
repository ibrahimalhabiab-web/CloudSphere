# GitLab Installation and CI/CD Guide

## 1. What is implemented

The project deploys GitLab Community Edition as a self-managed Docker service on its own Azure VM. GitLab Runner runs on the separate monitoring VM and uses the Docker executor. The repository pipeline validates every change and provides a protected manual deployment step for the monitoring stack.

## 2. First sign-in

Display the GitLab URL and host address:

```bash
terraform -chdir=terraform output gitlab_url
terraform -chdir=terraform output gitlab_public_ip_address
```

Retrieve the initial password without copying it into source control:

```bash
ssh azureadmin@GITLAB_PUBLIC_IP \
  cat /opt/gitlab-stack/secrets/gitlab_root_password.txt
```

Sign in with username `root`, rotate the password, and store the new credential in the approved password manager. The generated file affects only the first database initialization and does not reset an existing GitLab password.

## 3. Create the internal repository

1. Create a group such as `internal-platform`.
2. Create a blank project such as `gitlab-observability-platform`.
3. Keep the default branch named `main`.
4. Under **Settings > Repository > Protected branches**, protect `main` and require merge requests for normal changes.
5. Add project members with the lowest suitable roles.

Push this repository over HTTP:

```bash
git remote add internal http://GITLAB_PUBLIC_IP/internal-platform/gitlab-observability-platform.git
git push -u internal main
```

Or add an SSH key to the GitLab user profile and use the configured repository SSH port:

```bash
git remote add internal \
  ssh://git@GITLAB_PUBLIC_IP:2222/internal-platform/gitlab-observability-platform.git
git push -u internal main
```

Host administration remains on SSH port `22`; Git repository SSH uses `2222`.

## 4. Register GitLab Runner

GitLab Runner registration uses the current runner authentication-token workflow.

1. Open the project in GitLab.
2. Go to **Settings > CI/CD > Runners**.
3. Create a project runner.
4. Allow untagged jobs or assign tags compatible with the pipeline.
5. Copy the authentication token beginning with `glrt-`.
6. On the monitoring VM, run:

   ```bash
   ssh azureadmin@MONITORING_PUBLIC_IP
   cd /opt/monitoring
   RUNNER_AUTH_TOKEN='PASTE_GLRT_AUTHENTICATION_TOKEN' ./scripts/register-runner.sh
   ```

7. Return to GitLab and confirm that the runner is online.

The script stores generated Runner configuration in the `monitoring_gitlab_runner_config` Docker volume. The token is passed only through the process environment and must not be written to `.env`, shell history, screenshots, tickets, or Git.

When `GITLAB_PRIVATE_URL` is present, the script registers through that private VNet address and sets Runner's `clone_url` to the same address. Runner scope, tags, protected status, and the ability to run untagged jobs are controlled when the runner is created in GitLab, not by embedding those policies in the registration command.

## 5. Pipeline jobs

| Job | Stage | Purpose |
|---|---|---|
| `terraform_validate` | validate | Terraform formatting, initialization without backend, and validation |
| `shellcheck` | validate | Static analysis for deployment, health, backup, restore, and operations scripts |
| `python_and_dashboards` | validate | Python syntax and both Grafana dashboard JSON documents |
| `compose_validate` | validate | Monitoring and GitLab Compose model validation with CI-only placeholder secrets |
| `secret_detection` | test | GitLab-maintained committed-secret scanning |
| `unit_tests` | test | Demo application metric and reset tests |
| `deploy_monitoring` | deploy | Protected manual transfer and restart of the monitoring stack |

Terraform apply and destroy are intentionally not automatic pipeline jobs. Infrastructure changes require an operator to review the Terraform plan and approve the local deployment script.

## 6. Deployment variables

Create these under **Settings > CI/CD > Variables**. Protect and mask sensitive values.

| Variable | Recommended protection | Purpose |
|---|---|---|
| `MONITORING_HOST` | Protected | Private monitoring VM address when Runner is inside the VNet |
| `MONITORING_USER` | Protected | Linux deployment account, normally `azureadmin` |
| `MONITORING_SSH_PORT` | Protected | Host administration port, normally `22` |
| `DEPLOY_SSH_PRIVATE_KEY` | Protected, masked, file variable if available | Dedicated least-privilege deployment key |
| `DEPLOY_KNOWN_HOSTS` | Protected, file variable recommended | Pre-verified SSH host-key entry for the monitoring VM |
| `GRAFANA_URL` | Protected, not secret | Environment link displayed by GitLab |

Use a dedicated deployment key rather than the administrator's personal SSH key. Authorize it only on the monitoring VM and rotate it on a defined schedule.

Create the known-hosts value from a trusted workstation and verify the fingerprint through the already established administrator session before saving it as a protected file variable:

```bash
ssh-keyscan -p 22 -H MONITORING_PRIVATE_IP > monitoring_known_hosts
ssh azureadmin@MONITORING_PUBLIC_IP \
  'ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub'
ssh-keygen -lf monitoring_known_hosts
```

Do not accept an unverified `ssh-keyscan` result inside the pipeline. Update `DEPLOY_KNOWN_HOSTS` after a legitimate host-key rotation.

## 7. Merge-request demonstration

```bash
git switch -c feature/demo-pipeline
printf '\n' >> docs/DEMO_GUIDE.md
git add docs/DEMO_GUIDE.md
git commit -m "Demonstrate merge request pipeline"
git push -u internal feature/demo-pipeline
```

Then:

1. Open the merge request in GitLab.
2. Show the commit, changed file, reviewer, and pipeline widget.
3. Open the pipeline and show validation/test jobs.
4. Merge after the pipeline passes.
5. Open the default-branch pipeline and demonstrate the manual deployment job only if deployment variables are configured.

Do not create meaningless commits in the final repository merely for a presentation; use a genuine documentation or configuration improvement.

## 8. Troubleshooting

### Runner is offline

```bash
cd /opt/monitoring
docker compose --env-file .env ps gitlab-runner
docker compose --env-file .env logs --tail=200 gitlab-runner
docker compose --env-file .env exec -T gitlab-runner gitlab-runner list
```

Confirm the Runner can reach `GITLAB_PRIVATE_URL` and that its authentication token has not been revoked.

### Pipeline is pending

- Confirm the runner is online and permitted to run untagged jobs.
- Check protected-runner and protected-branch settings.
- Confirm Runner and GitLab versions are compatible.
- Check Runner logs for Docker executor or image-pull errors.

### Deployment job cannot connect

- Use the monitoring VM's private IP when Runner is inside the Azure VNet.
- Confirm the deployment public key exists in the target user's `authorized_keys`.
- Verify the CI private key preserves line breaks.
- Confirm the target directory is owned by the deployment account.
- Never disable host-key checking as a permanent workaround.

## 9. Official guidance

- [Install GitLab with Docker Compose](https://docs.gitlab.com/install/docker/installation/)
- [Register GitLab Runner](https://docs.gitlab.com/runner/register/)
- [Runner private clone URL configuration](https://docs.gitlab.com/runner/configuration/advanced-configuration/#how-clone-url-works)
- [GitLab Runner monitoring](https://docs.gitlab.com/runner/monitoring/)
- [GitLab health checks](https://docs.gitlab.com/administration/monitoring/health_check/)
