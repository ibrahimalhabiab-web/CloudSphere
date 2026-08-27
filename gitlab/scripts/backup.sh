#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${STACK_ROOT}/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cd "${STACK_ROOT}"

[[ -f .env ]] || {
  printf '[gitlab-backup] .env is missing.\n' >&2
  exit 1
}

set -a
# shellcheck disable=SC1091
source .env
set +a

install -d -m 0700 "${BACKUP_DIR}"

printf '[gitlab-backup] Creating the GitLab application backup.\n'
docker compose --env-file .env exec -T gitlab gitlab-backup create

printf '[gitlab-backup] Copying the latest application archive.\n'
docker run --rm \
  -v "${GITLAB_HOME}/data:/source:ro" \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.22 \
  sh -c 'latest="$(ls -t /source/backups/*_gitlab_backup.tar | head -n 1)"; test -n "$latest"; cp "$latest" /backup/'

printf '[gitlab-backup] Archiving configuration and secrets separately.\n'
docker run --rm \
  -v "${GITLAB_HOME}/config:/source:ro" \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.22 \
  sh -c "cd /source && tar -czf '/backup/gitlab-config-${STAMP}.tar.gz' ."

sha256sum "${BACKUP_DIR}"/*_gitlab_backup.tar "${BACKUP_DIR}/gitlab-config-${STAMP}.tar.gz" > "${BACKUP_DIR}/checksums-${STAMP}.sha256"
printf '[gitlab-backup] Backups written to %s. Copy them to encrypted off-VM storage.\n' "${BACKUP_DIR}"
