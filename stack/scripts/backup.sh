#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${STACK_ROOT}/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

install -d -m 0700 "${BACKUP_DIR}"

backup_volume() {
  local volume="$1"
  local archive="$2"
  docker run --rm \
    -v "${volume}:/source:ro" \
    -v "${BACKUP_DIR}:/backup" \
    alpine:3.22 \
    sh -c "cd /source && tar -czf '/backup/${archive}' ."
}

backup_volume monitoring_prometheus_data "prometheus-${STAMP}.tar.gz"
backup_volume monitoring_alertmanager_data "alertmanager-${STAMP}.tar.gz"
backup_volume monitoring_grafana_data "grafana-${STAMP}.tar.gz"

sha256sum "${BACKUP_DIR}"/*-"${STAMP}".tar.gz > "${BACKUP_DIR}/checksums-${STAMP}.sha256"
printf '[backup] Backups written to %s\n' "${BACKUP_DIR}"
