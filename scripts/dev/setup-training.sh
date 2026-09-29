#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "$script_dir/../.." && pwd)"
source "$script_dir/project-env.sh"
update=false
case "${1:-}" in
  '') ;;
  --update) update=true ;;
  *) echo "Usage: $0 [--update]" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
[[ "$(uname -m)" == x86_64 ]] || { echo 'Training is currently validated for Linux x86_64 NVIDIA GPUs.' >&2; exit 1; }
command -v uv >/dev/null
mkdir -p "$QUORIDOR_ENV_REPORT_DIR" "$UV_CACHE_DIR" "$UV_PYTHON_INSTALL_DIR"
exec 9>"$QUORIDOR_ENV_REPORT_DIR/training-setup.lock"
flock 9
# Select the latest stable managed CPython; callers can request a compatible minor
# during a transition, e.g. QUORIDOR_PYTHON=3.14. No system Python is modified.
python_request="${QUORIDOR_PYTHON:-3}"
python_args=()
if [[ "$update" == true ]]; then python_args+=(--upgrade); fi
uv python install "${python_args[@]}" "$python_request"
export UV_PROJECT_ENVIRONMENT="$QUORIDOR_TRAINING_ENV"
export UV_LINK_MODE=copy
if [[ "$update" == true || ! -f "$workspace_root/tools/training/uv.lock" ]]; then
  uv lock --project "$workspace_root/tools/training" --python "$python_request" --managed-python --upgrade
fi
uv sync --project "$workspace_root/tools/training" --python "$python_request" --managed-python --locked
# Some inference libraries create auxiliary files relative to the working
# directory. Keep smoke-test outputs out of the checkout and remove them.
verification_dir="$(mktemp -d)"
trap 'rm -rf -- "$verification_dir"' EXIT
(
  cd "$verification_dir"
  "$UV_PROJECT_ENVIRONMENT/bin/python" "$workspace_root/tools/training/verify_environment.py" \
    --output "$QUORIDOR_ENV_REPORT_DIR/training-environment.json"
)
