#!/usr/bin/env bash
set -euo pipefail
root_dir=$(git rev-parse --show-toplevel)
index_dir="$root_dir/.artifacts/ai-sigma/resume-20261002/COMPLETED-FPU"
export GIT_INDEX_FILE="$index_dir/private-index"
trap 'rm -f "$GIT_INDEX_FILE" "$GIT_INDEX_FILE.lock"' EXIT
git read-tree HEAD
git add -- "$@"
git commit -m "${SIGMA_COMMIT_MESSAGE:?message required}"
