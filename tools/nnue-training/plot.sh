#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
plot_python="${QUORIDOR_PLOT_PYTHON:-/home/vscode/.cache/inference/envs/quoridor-learning-plots/bin/python}"
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/home/vscode/.cache/inference/matplotlib}"
exec "$plot_python" "$repo_root/tools/nnue-training/plot.py" "$@"
