#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_ROOT}"

command -v docker >/dev/null 2>&1 || {
  printf '[gitlab] Docker is required.\n' >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  printf '[gitlab] Docker Compose v2 is required.\n' >&2
  exit 1
}

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf '[gitlab] Created .env from .env.example.\n'
fi

upsert_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '%s=%s\n' "${key}" "${value}" >> .env
  fi
}

if [[ -n "${GITLAB_EXTERNAL_URL:-}" ]]; then
  upsert_env GITLAB_EXTERNAL_URL "${GITLAB_EXTERNAL_URL}"
fi
if [[ -n "${GITLAB_HOSTNAME:-}" ]]; then
  upsert_env GITLAB_HOSTNAME "${GITLAB_HOSTNAME}"
fi

"${SCRIPT_DIR}/init-secrets.sh"

printf '[gitlab] Validating the Compose model.\n'
docker compose --env-file .env config --quiet

printf '[gitlab] Pulling the pinned GitLab image.\n'
docker compose --env-file .env pull

printf '[gitlab] Starting GitLab. First initialization can take 10-20 minutes.\n'
docker compose --env-file .env up -d --remove-orphans

"${SCRIPT_DIR}/health-check.sh" --wait
