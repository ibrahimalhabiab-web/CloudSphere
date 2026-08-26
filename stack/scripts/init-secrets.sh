#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SECRET_DIR="${STACK_ROOT}/secrets"
PASSWORD_FILE="${SECRET_DIR}/grafana_admin_password.txt"

command -v openssl >/dev/null 2>&1 || {
  printf 'OpenSSL is required to generate the Grafana password.\n' >&2
  exit 1
}

install -d -m 0700 "${SECRET_DIR}"

if [[ ! -s "${PASSWORD_FILE}" ]]; then
  umask 077
  openssl rand -base64 32 | tr -d '\n' > "${PASSWORD_FILE}"
  printf '\n' >> "${PASSWORD_FILE}"
  chmod 0600 "${PASSWORD_FILE}"
  printf '[secrets] Generated %s\n' "${PASSWORD_FILE}"
else
  chmod 0600 "${PASSWORD_FILE}"
  printf '[secrets] Reusing the existing Grafana password file.\n'
fi
