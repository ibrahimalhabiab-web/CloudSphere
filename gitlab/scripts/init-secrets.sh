#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SECRET_DIR="${STACK_ROOT}/secrets"
PASSWORD_FILE="${SECRET_DIR}/gitlab_root_password.txt"

command -v openssl >/dev/null 2>&1 || {
  printf '[gitlab-secrets] OpenSSL is required.\n' >&2
  exit 1
}

install -d -m 0700 "${SECRET_DIR}"

if [[ ! -s "${PASSWORD_FILE}" ]]; then
  umask 077
  openssl rand -base64 36 | tr -d '\n' > "${PASSWORD_FILE}"
  printf '\n' >> "${PASSWORD_FILE}"
  chmod 0600 "${PASSWORD_FILE}"
  printf '[gitlab-secrets] Generated the initial root password file.\n'
else
  chmod 0600 "${PASSWORD_FILE}"
  printf '[gitlab-secrets] Reusing the existing initial root password file.\n'
fi
