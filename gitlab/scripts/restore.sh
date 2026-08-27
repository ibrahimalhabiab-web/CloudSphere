#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_ROOT}"

if [[ "${CONFIRM_RESTORE:-}" != "yes" || -z "${BACKUP_ID:-}" ]]; then
  printf 'No data was changed. Restore requires the exact same GitLab version.\n'
  printf 'Place the archive in the GitLab backups directory, then run:\n'
  printf '  CONFIRM_RESTORE=yes BACKUP_ID=TIMESTAMP_VERSION ./scripts/restore.sh\n'
  exit 2
fi

printf '[gitlab-restore] Stopping application processes.\n'
docker compose --env-file .env exec -T gitlab gitlab-ctl stop puma
docker compose --env-file .env exec -T gitlab gitlab-ctl stop sidekiq

printf '[gitlab-restore] Restoring %s.\n' "${BACKUP_ID}"
docker compose --env-file .env exec -T gitlab gitlab-backup restore BACKUP="${BACKUP_ID}" force=yes

docker compose --env-file .env restart gitlab
docker compose --env-file .env exec -T gitlab gitlab-rake gitlab:check SANITIZE=true
printf '[gitlab-restore] Restore and GitLab check completed.\n'
