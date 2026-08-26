#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${PROJECT_ROOT}/terraform"
STACK_DIR="${PROJECT_ROOT}/stack"

failures=0

run_check() {
  local label="$1"
  shift
  printf '[check] %s\n' "${label}"
  if ! "$@"; then
    failures=$((failures + 1))
  fi
}

if command -v terraform >/dev/null 2>&1; then
  run_check "Terraform formatting" terraform -chdir="${TF_DIR}" fmt -check -recursive
  if [[ -d "${TF_DIR}/.terraform" ]]; then
    run_check "Terraform validation" terraform -chdir="${TF_DIR}" validate
  else
    printf '[skip] Terraform validate requires terraform init.\n'
  fi
else
  printf '[skip] Terraform is not installed.\n'
fi

if command -v python3 >/dev/null 2>&1; then
  run_check "Demo application syntax" python3 -m py_compile "${STACK_DIR}/demo-app/app.py"
  run_check "Grafana dashboard JSON" python3 -m json.tool "${STACK_DIR}/grafana/dashboards/operations-overview.json"
else
  printf '[skip] Python 3 is not installed.\n'
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  if [[ ! -f "${STACK_DIR}/secrets/grafana_admin_password.txt" ]]; then
    "${STACK_DIR}/scripts/init-secrets.sh" >/dev/null
  fi
  run_check "Docker Compose model" docker compose --project-directory "${STACK_DIR}" --env-file "${STACK_DIR}/.env.example" -f "${STACK_DIR}/compose.yaml" config --quiet
else
  printf '[skip] Docker Compose is not installed.\n'
fi

if [[ "${failures}" -ne 0 ]]; then
  printf '[check] %s validation check(s) failed.\n' "${failures}" >&2
  exit 1
fi

printf '[check] All available validation checks passed.\n'
