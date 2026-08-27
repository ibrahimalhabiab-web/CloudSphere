#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_ROOT}"

[[ -f .env ]] || {
  printf '[runner] .env is missing. Deploy the monitoring stack first.\n' >&2
  exit 1
}

set -a
# shellcheck disable=SC1091
source .env
set +a

RUNNER_AUTH_TOKEN="${RUNNER_AUTH_TOKEN:-${1:-}}"
[[ "${RUNNER_AUTH_TOKEN}" == glrt-* ]] || {
  printf '[runner] Provide a GitLab runner authentication token beginning with glrt-.\n' >&2
  printf 'Usage: RUNNER_AUTH_TOKEN=glrt-... ./scripts/register-runner.sh\n' >&2
  exit 1
}

RUNNER_GITLAB_URL="${GITLAB_PRIVATE_URL:-${GITLAB_URL:-}}"
[[ "${RUNNER_GITLAB_URL}" =~ ^https?:// ]] || {
  printf '[runner] Set GITLAB_PRIVATE_URL or GITLAB_URL in .env to the self-managed GitLab URL.\n' >&2
  exit 1
}

registration_args=(
  --non-interactive
  --url "${RUNNER_GITLAB_URL}"
  --token "${RUNNER_AUTH_TOKEN}"
  --executor docker
  --docker-image alpine:3.22
  --docker-pull-policy if-not-present
  --description "azure-monitoring-docker-runner"
)

if [[ -n "${GITLAB_PRIVATE_URL:-}" ]]; then
  registration_args+=(--clone-url "${GITLAB_PRIVATE_URL}")
fi

printf '[runner] Registering a Docker executor through %s.\n' "${RUNNER_GITLAB_URL}"
docker compose --env-file .env run --rm gitlab-runner register "${registration_args[@]}"

docker compose --env-file .env restart gitlab-runner
docker compose --env-file .env exec -T gitlab-runner gitlab-runner list
docker compose --env-file .env exec -T gitlab-runner gitlab-runner verify
printf '[runner] Registration completed. Runner scope, tags, and protected status remain controlled in GitLab.\n'
printf '[runner] Do not store the authentication token in this repository.\n'
