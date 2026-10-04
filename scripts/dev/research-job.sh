#!/usr/bin/env bash
set -euo pipefail
research_job_scripts="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$research_job_scripts/project-env.sh"
export UV_PROJECT_ENVIRONMENT="${QUORIDOR_RESEARCH_TEAM_ENV:-${INFERENCE_CACHE_DIR:-$HOME/.cache/inference}/envs/quoridor-research-team}"
if [[ "$(realpath -m -- "$UV_PROJECT_ENVIRONMENT")" == "$(realpath -m -- "$QUORIDOR_TRAINING_ENV")" ]]; then
  echo "Research-job supervisor requires the separate research-team environment" >&2
  exit 2
fi
exec uv run --locked --project "$research_job_scripts/../../tools/research-team" python -B "$research_job_scripts/research-job.py" "$@"
