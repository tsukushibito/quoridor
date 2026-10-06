#!/usr/bin/env bash
set -euo pipefail
research_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$research_script_dir/project-env.sh"
export UV_PROJECT_ENVIRONMENT="${QUORIDOR_RESEARCH_SESSION_ENV:-${INFERENCE_CACHE_DIR:-$HOME/.cache/inference}/envs/quoridor-research-team}"
if [[ "$(realpath -m -- "$UV_PROJECT_ENVIRONMENT")" == "$(realpath -m -- "$QUORIDOR_TRAINING_ENV")" ]]; then
  echo "Task session tools require an environment separate from training" >&2
  exit 2
fi
exec uv run --locked --offline --no-sync --project "$research_script_dir/../../tools/research-session" python -B "$research_script_dir/research-session.py" "$@"
