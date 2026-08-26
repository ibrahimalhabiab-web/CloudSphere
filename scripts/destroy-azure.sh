#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${PROJECT_ROOT}/terraform"

command -v terraform >/dev/null 2>&1 || {
  printf 'Terraform is required.\n' >&2
  exit 1
}

if [[ "${CONFIRM_DESTROY:-}" != "yes" ]]; then
  printf 'No resources were changed. To destroy this project, run:\n'
  printf '  CONFIRM_DESTROY=yes ./scripts/destroy-azure.sh\n'
  exit 2
fi

terraform -chdir="${TF_DIR}" destroy
