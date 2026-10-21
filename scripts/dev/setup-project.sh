#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:-}"
case "$mode" in
  '' | --update | --python-only | --infrastructure-only) ;;
  *) echo "Usage: $0 [--update|--python-only|--infrastructure-only]" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
if [[ "$mode" != --python-only ]]; then
  infrastructure_args=()
  [[ "$mode" != --update ]] || infrastructure_args+=(--update)
  bash "$script_dir/setup-rust.sh" "${infrastructure_args[@]}"
  bash "$script_dir/verify-rust.sh"
  bash "$script_dir/setup-beads.sh" "${infrastructure_args[@]}"
fi
[[ "$mode" != --infrastructure-only ]] || exit 0
source "$script_dir/project-env.sh"
mkdir -p "$QUORIDOR_ENV_REPORT_DIR" "$UV_CACHE_DIR" "$UV_PYTHON_INSTALL_DIR" "$(dirname -- "$QUORIDOR_PROJECT_ENV")"
# One environment writer. Current runtime consumers must stop before setup.
exec 9>"$QUORIDOR_PROJECT_ENV.setup.lock"
flock -n 9 || { echo "Another Python environment writer is active" >&2; exit 2; }
uv python install 3.14.7
# Dependency upgrades require an explicit reviewed root pyproject/lock change;
# --update above updates infrastructure, never the scientific package pins.
uv sync --project "$QUORIDOR_PROJECT_ROOT" --locked --all-groups \
  --python 3.14.7 --managed-python --no-python-downloads
# Verify while the same exclusive writer is held; avoid nested reader-lock admission.
PYTHONSAFEPATH=1 PYTHONPATH="$QUORIDOR_CODE_ROOT/games/quoridor/python:$QUORIDOR_CODE_ROOT/shared/python" "$QUORIDOR_PROJECT_ENV/bin/python" -B \
  "$script_dir/verify-python-environment.py" --output "$QUORIDOR_ENV_REPORT_DIR/python-environment.json"
