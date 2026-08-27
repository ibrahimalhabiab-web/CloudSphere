#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${PROJECT_ROOT}/terraform"
MONITORING_STACK_DIR="${PROJECT_ROOT}/stack"
GITLAB_STACK_DIR="${PROJECT_ROOT}/gitlab"

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

wait_for_ssh() {
  local label="$1"
  local remote="$2"
  local attempt
  log "Waiting for SSH on ${label} (${remote#*@})"
  for ((attempt = 1; attempt <= 60; attempt++)); do
    if ssh "${SSH_OPTIONS[@]}" "${remote}" true >/dev/null 2>&1; then
      return 0
    fi
    if ((attempt % 6 == 0)); then
      log "SSH is not ready on ${label} yet (${attempt}/60 checks)."
    fi
    sleep 10
  done
  fail "SSH for ${label} did not become available within ten minutes. Review Azure boot diagnostics."
}

for command_name in terraform az ssh tar; do
  require_command "${command_name}"
done

[[ -f "${TF_DIR}/terraform.tfvars" ]] || fail "Copy terraform/terraform.tfvars.example to terraform/terraform.tfvars and set trusted CIDRs first."
az account show >/dev/null 2>&1 || fail "Azure CLI is not authenticated. Run: az login"

log "Formatting and initializing Terraform"
terraform -chdir="${TF_DIR}" fmt -recursive
terraform -chdir="${TF_DIR}" init
terraform -chdir="${TF_DIR}" validate

log "Creating and reviewing the combined platform plan"
terraform -chdir="${TF_DIR}" plan -out=platform.tfplan

if [[ "${AUTO_APPROVE:-false}" != "true" ]]; then
  read -r -p "Apply this GitLab and monitoring plan to Azure? [y/N] " answer
  [[ "${answer}" =~ ^[Yy]$ ]] || fail "Deployment cancelled before Azure resources were changed."
fi

log "Applying the approved infrastructure plan"
terraform -chdir="${TF_DIR}" apply platform.tfplan

MONITORING_PUBLIC_IP="$(terraform -chdir="${TF_DIR}" output -raw public_ip_address)"
GITLAB_PUBLIC_IP="$(terraform -chdir="${TF_DIR}" output -raw gitlab_public_ip_address)"
GITLAB_PRIVATE_IP="$(terraform -chdir="${TF_DIR}" output -raw gitlab_private_ip_address)"
ADMIN_USER="$(terraform -chdir="${TF_DIR}" output -raw admin_username)"
GITLAB_URL="$(terraform -chdir="${TF_DIR}" output -raw gitlab_url)"
SSH_OPTIONS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 -o ServerAliveInterval=30 -o ServerAliveCountMax=20)
MONITORING_REMOTE="${ADMIN_USER}@${MONITORING_PUBLIC_IP}"
GITLAB_REMOTE="${ADMIN_USER}@${GITLAB_PUBLIC_IP}"

wait_for_ssh "monitoring VM" "${MONITORING_REMOTE}"
wait_for_ssh "GitLab VM" "${GITLAB_REMOTE}"

log "Waiting for cloud initialization on both VMs"
ssh "${SSH_OPTIONS[@]}" "${MONITORING_REMOTE}" 'sudo cloud-init status --wait'
ssh "${SSH_OPTIONS[@]}" "${GITLAB_REMOTE}" 'sudo cloud-init status --wait'

log "Uploading and starting self-managed GitLab"
# The following values are intentionally expanded locally from trusted Terraform outputs.
# shellcheck disable=SC2029
ssh "${SSH_OPTIONS[@]}" "${GITLAB_REMOTE}" "sudo install -d -o '${ADMIN_USER}' -g '${ADMIN_USER}' /opt/gitlab-stack"
tar -C "${GITLAB_STACK_DIR}" -czf - . | ssh "${SSH_OPTIONS[@]}" "${GITLAB_REMOTE}" 'tar -xzf - -C /opt/gitlab-stack'
# shellcheck disable=SC2029
ssh "${SSH_OPTIONS[@]}" "${GITLAB_REMOTE}" \
  "cd /opt/gitlab-stack && chmod +x scripts/*.sh && GITLAB_EXTERNAL_URL='${GITLAB_URL}' GITLAB_HOSTNAME='gitlab.internal' ./scripts/deploy-gitlab.sh"

log "Uploading the monitoring stack and wiring GitLab private targets"
# shellcheck disable=SC2029
ssh "${SSH_OPTIONS[@]}" "${MONITORING_REMOTE}" "sudo install -d -o '${ADMIN_USER}' -g '${ADMIN_USER}' /opt/monitoring"
tar -C "${MONITORING_STACK_DIR}" -czf - . | ssh "${SSH_OPTIONS[@]}" "${MONITORING_REMOTE}" 'tar -xzf - -C /opt/monitoring'
# shellcheck disable=SC2029
ssh "${SSH_OPTIONS[@]}" "${MONITORING_REMOTE}" "install -d /opt/monitoring/prometheus/file_sd && printf '%s\n' '- targets: [\"${GITLAB_PRIVATE_IP}:80\"]' '  labels:' '    role: gitlab-application' > /opt/monitoring/prometheus/file_sd/gitlab-metrics.yml && printf '%s\n' '- targets: [\"${GITLAB_PRIVATE_IP}:9100\"]' '  labels:' '    role: gitlab-host' > /opt/monitoring/prometheus/file_sd/gitlab-node.yml && printf '%s\n' '- targets: [\"http://${GITLAB_PRIVATE_IP}/-/health\"]' '  labels:' '    role: gitlab-application' > /opt/monitoring/prometheus/file_sd/gitlab-health.yml"
# shellcheck disable=SC2029
ssh "${SSH_OPTIONS[@]}" "${MONITORING_REMOTE}" \
  "cd /opt/monitoring && chmod +x scripts/*.sh && if [[ ! -f .env ]]; then cp .env.example .env; fi && sed -i 's|^GITLAB_URL=.*|GITLAB_URL=${GITLAB_URL}|' .env && sed -i 's|^GITLAB_PRIVATE_URL=.*|GITLAB_PRIVATE_URL=http://${GITLAB_PRIVATE_IP}|' .env && ./scripts/deploy-local.sh"

GRAFANA_URL="$(terraform -chdir="${TF_DIR}" output -raw grafana_url)"
PROMETHEUS_TUNNEL="$(terraform -chdir="${TF_DIR}" output -raw prometheus_tunnel_command)"

printf '\nCombined platform deployment completed.\n'
printf 'GitLab: %s\n' "${GITLAB_URL}"
printf 'GitLab user: root\n'
printf 'Initial GitLab password: ssh %s cat /opt/gitlab-stack/secrets/gitlab_root_password.txt\n' "${GITLAB_REMOTE}"
printf 'Git repository SSH port: 2222\n'
printf 'Grafana: %s\n' "${GRAFANA_URL}"
printf 'Grafana user: %s\n' "$(grep '^GRAFANA_ADMIN_USER=' "${MONITORING_STACK_DIR}/.env.example" | cut -d= -f2-)"
printf 'Grafana password: ssh %s sudo cat /opt/monitoring/secrets/grafana_admin_password.txt\n' "${MONITORING_REMOTE}"
printf 'Prometheus tunnel: %s\n' "${PROMETHEUS_TUNNEL}"
printf '\nNext: create a project runner in GitLab, then register it on the monitoring VM:\n'
printf '  ssh %s\n' "${MONITORING_REMOTE}"
printf "  cd /opt/monitoring && RUNNER_AUTH_TOKEN='PASTE_GLRT_AUTHENTICATION_TOKEN' ./scripts/register-runner.sh\n"
