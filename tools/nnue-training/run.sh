#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
training_python="${QUORIDOR_NNUE_PYTHON:-/home/vscode/.cache/inference/envs/quoridor-training/bin/python}"
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
exec "$training_python" "$repo_root/tools/nnue-training/train.py" "$@"
