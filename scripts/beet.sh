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

export HOME="${repo_root}/state/home"
export XDG_CACHE_HOME="${repo_root}/state/xdg-cache"
export BEETSDIR="${repo_root}/config"

exec "${repo_root}/.venv/bin/beet" "$@"
