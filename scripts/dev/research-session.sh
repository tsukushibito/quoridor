#!/usr/bin/env bash
set -euo pipefail
research_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$research_script_dir/project-env.sh" python -B "$research_script_dir/research-session.py" "$@"
