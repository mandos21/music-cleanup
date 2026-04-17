#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="${repo_root}/.venv"

python3 -m venv "${venv_path}"
source "${venv_path}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation -e "${repo_root}[dev]"

echo
echo "Environment ready."
echo "Activate with: source ${venv_path}/bin/activate"
