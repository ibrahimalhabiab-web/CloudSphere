#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_ROOT}"

command -v docker >/dev/null 2>&1 || {
  printf '[stack] Docker is required.\n' >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  printf '[stack] Docker Compose v2 is required.\n' >&2
  exit 1
}

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf '[stack] Created .env from the version-pinned example.\n'
fi

"${SCRIPT_DIR}/init-secrets.sh"

printf '[stack] Validating the Compose model.\n'
docker compose --env-file .env config --quiet

printf '[stack] Pulling upstream images.\n'
docker compose --env-file .env pull --ignore-buildable

printf '[stack] Building and starting the platform.\n'
docker compose --env-file .env up -d --build --remove-orphans

printf '[stack] Waiting for Grafana health.\n'
for attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:3000/api/health >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 60 ]]; then
    docker compose --env-file .env ps
    printf '[stack] Grafana did not become healthy within five minutes.\n' >&2
    exit 1
  fi
  sleep 5
done

sleep 30 # Allow newly-created services to settle.
"${SCRIPT_DIR}/health-check.sh"
