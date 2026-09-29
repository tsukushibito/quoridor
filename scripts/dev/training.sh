#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "$script_dir/../.." && pwd)"
source "$script_dir/project-env.sh"
export UV_PROJECT_ENVIRONMENT="$QUORIDOR_TRAINING_ENV"
export UV_LINK_MODE=copy
exec uv run --project "$workspace_root/tools/training" --locked --managed-python "$@"
