#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_ROOT}"

[[ -f .env ]] || {
  printf '[gitlab-health] .env is missing. Run deploy-gitlab.sh first.\n' >&2
  exit 1
}

set -a
# shellcheck disable=SC1091
source .env
set +a

health_url="http://127.0.0.1/-/health"
node_metrics_url="http://127.0.0.1:9100/metrics"
attempts=1
delay=0
if [[ "${1:-}" == "--wait" ]]; then
  attempts=120
  delay=10
fi

for attempt in $(seq 1 "${attempts}"); do
  if docker exec internal-gitlab docker exec internal-gitlab curl -fsS --max-time 10 "${health_url}" | grep -q 'GitLab OK' && \
    curl -fsS --max-time 10 "${node_metrics_url}" >/dev/null; then
    printf '[gitlab-health] PASS  %s\n' "${health_url}"
    printf '[gitlab-health] PASS  %s\n' "${node_metrics_url}"
    docker compose --env-file .env ps
    exit 0
  fi
  if [[ "${attempt}" -lt "${attempts}" ]]; then
    sleep "${delay}"
  fi
done

docker compose --env-file .env ps
docker compose --env-file .env logs --tail=80 gitlab
printf '[gitlab-health] FAIL  GitLab did not become healthy at %s.\n' "${health_url}" >&2
printf '[gitlab-health] FAIL  Node Exporter must also respond at %s.\n' "${node_metrics_url}" >&2
exit 1
