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

dotenv_value() {
  local key="$1"
  local line
  local value=""

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%$'\r'}"
    [[ "${line}" =~ ^[[:space:]]*(#|$) ]] && continue
    if [[ "${line}" =~ ^[[:space:]]*(export[[:space:]]+)?${key}[[:space:]]*=(.*)$ ]]; then
      value="${BASH_REMATCH[2]}"
    fi
  done < .env

  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "${#value}" -ge 2 ]]; then
    case "${value:0:1}${value: -1}" in
      "\"\"" | "''") value="${value:1:${#value}-2}" ;;
    esac
  fi
  printf '%s' "${value}"
}

public_frontend_enabled="${PUBLIC_FRONTEND_ENABLED:-}"
if [[ -z "${public_frontend_enabled}" ]]; then
  public_frontend_enabled="$(dotenv_value PUBLIC_FRONTEND_ENABLED)"
fi
public_frontend_enabled="${public_frontend_enabled:-false}"
public_frontend_enabled="${public_frontend_enabled,,}"

case "${public_frontend_enabled}" in
  true | false) ;;
  *)
    printf '[stack] PUBLIC_FRONTEND_ENABLED must be true or false, not %q.\n' "${public_frontend_enabled}" >&2
    exit 1
    ;;
esac

compose=(docker compose --env-file .env)
public_compose=(docker compose --env-file .env --profile public)

if [[ "${public_frontend_enabled}" == "true" ]]; then
  public_domain="${PUBLIC_DOMAIN:-}"
  if [[ -z "${public_domain}" ]]; then
    public_domain="$(dotenv_value PUBLIC_DOMAIN)"
  fi
  if [[ -z "${public_domain}" ]]; then
    printf '[stack] PUBLIC_DOMAIN is required when PUBLIC_FRONTEND_ENABLED=true.\n' >&2
    exit 1
  fi
  if [[ "${#public_domain}" -gt 253 ]] || \
     [[ ! "${public_domain}" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$ ]]; then
    printf '[stack] PUBLIC_DOMAIN must be a DNS hostname without a scheme, port, or path.\n' >&2
    exit 1
  fi
  export PUBLIC_DOMAIN="${public_domain}"

  public_apex_domain="${PUBLIC_APEX_DOMAIN:-}"
  if [[ -z "${public_apex_domain}" ]]; then
    public_apex_domain="$(dotenv_value PUBLIC_APEX_DOMAIN)"
  fi
  public_apex_domain="${public_apex_domain:-cloudsphere-sda.online}"
  if [[ "${#public_apex_domain}" -gt 253 ]] || \
     [[ ! "${public_apex_domain}" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$ ]]; then
    printf '[stack] PUBLIC_APEX_DOMAIN must be a DNS hostname without a scheme, port, or path.\n' >&2
    exit 1
  fi
  if [[ "${public_apex_domain,,}" == "${public_domain,,}" ]]; then
    printf '[stack] PUBLIC_APEX_DOMAIN must differ from PUBLIC_DOMAIN.\n' >&2
    exit 1
  fi
  export PUBLIC_APEX_DOMAIN="${public_apex_domain}"

  compose=("${public_compose[@]}")
  printf '[stack] Public HTTPS profile enabled for %s (apex redirect: %s).\n' \
    "${PUBLIC_DOMAIN}" "${PUBLIC_APEX_DOMAIN}"
else
  printf '[stack] Public HTTPS profile disabled.\n'
fi

"${SCRIPT_DIR}/init-secrets.sh"

printf '[stack] Validating the Compose model.\n'
"${compose[@]}" config --quiet

if [[ "${public_frontend_enabled}" == "false" ]]; then
  # Stop a previously enabled proxy while preserving its certificate volumes.
  "${public_compose[@]}" stop caddy cloudsphere-public
  "${public_compose[@]}" rm --force caddy cloudsphere-public
fi

printf '[stack] Pulling upstream images.\n'
"${compose[@]}" pull --ignore-buildable

printf '[stack] Building and starting the platform.\n'
"${compose[@]}" up -d --build --remove-orphans

if [[ "${public_frontend_enabled}" == "true" ]]; then
  for public_service in cloudsphere-public caddy; do
    if [[ -z "$("${compose[@]}" ps --status running --quiet "${public_service}")" ]]; then
      "${compose[@]}" logs --tail=100 "${public_service}"
      printf '[stack] Public service %s did not remain running.\n' "${public_service}" >&2
      exit 1
    fi
  done
fi

printf '[stack] Waiting for Grafana health.\n'
for attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:3000/api/health >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 60 ]]; then
    "${compose[@]}" ps
    printf '[stack] Grafana did not become healthy within five minutes.\n' >&2
    exit 1
  fi
  sleep 5
done

sleep 30 # Allow newly-created services to settle.
"${SCRIPT_DIR}/health-check.sh"
