#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_ROOT}"

checks=(
  "Prometheus|http://127.0.0.1:9090/-/ready"
  "Alertmanager|http://127.0.0.1:9093/-/ready"
  "Grafana|http://127.0.0.1:3000/api/health"
  "CloudSphere application|http://127.0.0.1:8000/health"
  "CloudSphere metrics|http://127.0.0.1:8000/metrics"
  "GitLab Runner metrics|http://127.0.0.1:9252/metrics"
)

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  if [[ "${GITLAB_PRIVATE_URL:-}" =~ ^https?:// ]]; then
    checks+=("GitLab private health|${GITLAB_PRIVATE_URL%/}/-/health")
  fi
fi

failures=0
for item in "${checks[@]}"; do
  label="${item%%|*}"
  url="${item#*|}"
  if curl -fsS --max-time 5 "${url}" >/dev/null; then
    printf '[health] PASS  %s\n' "${label}"
  else
    printf '[health] FAIL  %s (%s)\n' "${label}" "${url}" >&2
    failures=$((failures + 1))
  fi
done

docker compose --env-file .env ps

if [[ "${failures}" -ne 0 ]]; then
  exit 1
fi

printf '[health] All service checks passed.\n'
