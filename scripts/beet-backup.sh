#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${repo_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${repo_root}/.env"
  set +a
fi

mkdir -p \
  "${repo_root}/state/xdg-cache" \
  "${repo_root}/state/beets" \
  "${repo_root}/state/home"

latest_backup_db="$(
  ls -1t /home/mandos/dev/musiclibrary.db.backup-* 2>/dev/null | head -n 1
)"
backup_db="${BEETS_BACKUP_DB:-${latest_backup_db}}"

if [[ -z "${backup_db}" ]]; then
  printf 'No backup beets database found. Set BEETS_BACKUP_DB to a backup DB path.\n' >&2
  exit 1
fi

if [[ ! -f "${backup_db}" ]]; then
  printf 'Backup beets database does not exist: %s\n' "${backup_db}" >&2
  exit 1
fi

export HOME="${repo_root}/state/home"
export XDG_CACHE_HOME="${repo_root}/state/xdg-cache"
export BEETSDIR="${repo_root}/config"

exec "${repo_root}/.venv/bin/beet" \
  -c "${repo_root}/config/backup.yaml" \
  -l "${backup_db}" \
  "$@"
