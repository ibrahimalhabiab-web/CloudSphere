#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${PROJECT_ROOT}/terraform"
STACK_DIR="${PROJECT_ROOT}/stack"

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

for command_name in terraform az ssh tar; do
  require_command "${command_name}"
done

[[ -f "${TF_DIR}/terraform.tfvars" ]] || fail "Copy terraform/terraform.tfvars.example to terraform/terraform.tfvars and set admin_source_cidr first."
az account show >/dev/null 2>&1 || fail "Azure CLI is not authenticated. Run: az login"

log "Formatting and initializing Terraform"
terraform -chdir="${TF_DIR}" fmt -recursive
terraform -chdir="${TF_DIR}" init
terraform -chdir="${TF_DIR}" validate

log "Creating and reviewing the Terraform execution plan"
terraform -chdir="${TF_DIR}" plan -out=monitoring.tfplan

if [[ "${AUTO_APPROVE:-false}" != "true" ]]; then
  read -r -p "Apply this plan to Azure? [y/N] " answer
  [[ "${answer}" =~ ^[Yy]$ ]] || fail "Deployment cancelled before Azure resources were changed."
fi

log "Applying the approved infrastructure plan"
terraform -chdir="${TF_DIR}" apply monitoring.tfplan

PUBLIC_IP="$(terraform -chdir="${TF_DIR}" output -raw public_ip_address)"
ADMIN_USER="$(terraform -chdir="${TF_DIR}" output -raw admin_username)"
SSH_OPTIONS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)
REMOTE="${ADMIN_USER}@${PUBLIC_IP}"

log "Waiting for SSH on ${PUBLIC_IP}"
for attempt in $(seq 1 60); do
  if ssh "${SSH_OPTIONS[@]}" "${REMOTE}" true >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 60 ]]; then
    fail "SSH did not become available within ten minutes. Review Azure boot diagnostics."
  fi
  sleep 10
done

log "Waiting for cloud initialization to finish"
ssh "${SSH_OPTIONS[@]}" "${REMOTE}" 'sudo cloud-init status --wait'
ssh "${SSH_OPTIONS[@]}" "${REMOTE}" "sudo install -d -o '${ADMIN_USER}' -g '${ADMIN_USER}' /opt/monitoring"

log "Uploading the version-controlled monitoring stack"
tar -C "${STACK_DIR}" -czf - . | ssh "${SSH_OPTIONS[@]}" "${REMOTE}" 'tar -xzf - -C /opt/monitoring'

log "Starting and verifying the monitoring services"
ssh "${SSH_OPTIONS[@]}" "${REMOTE}" 'cd /opt/monitoring && chmod +x scripts/*.sh && ./scripts/deploy-local.sh'

GRAFANA_URL="$(terraform -chdir="${TF_DIR}" output -raw grafana_url)"
TUNNEL_COMMAND="$(terraform -chdir="${TF_DIR}" output -raw prometheus_tunnel_command)"

printf '\nDeployment completed.\n'
printf 'Grafana: %s\n' "${GRAFANA_URL}"
printf 'Grafana user: %s\n' "$(grep '^GRAFANA_ADMIN_USER=' "${STACK_DIR}/.env.example" | cut -d= -f2-)"
printf 'Retrieve the Grafana password: ssh %s sudo cat /opt/monitoring/secrets/grafana_admin_password.txt\n' "${REMOTE}"
printf 'Prometheus tunnel: %s\n' "${TUNNEL_COMMAND}"
