#!/usr/bin/env bash
set -euo pipefail
research_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
research_checkout="$(cd -- "$research_script_dir/../.." && pwd)"
source "$research_script_dir/project-env.sh"
export UV_PROJECT_ENVIRONMENT="${QUORIDOR_RESEARCH_TEAM_ENV:-${INFERENCE_CACHE_DIR:-$HOME/.cache/inference}/envs/quoridor-research-team}"
if [[ "$(realpath -m -- "$UV_PROJECT_ENVIRONMENT")" == "$(realpath -m -- "$QUORIDOR_TRAINING_ENV")" ]]; then
  echo "Research-team client requires an environment separate from QUORIDOR_TRAINING_ENV" >&2
  exit 2
fi
exec uv run --locked --project "$research_checkout/tools/research-team" python "$research_script_dir/research-team.py" "$@"
