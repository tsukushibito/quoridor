#!/usr/bin/env bash
# Source from the project helpers; resolve the same store from every worktree.
beads_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
beads_common_dir="$(git -C "$beads_script_dir" rev-parse --path-format=absolute --git-common-dir)"
beads_project_root="$(dirname -- "$beads_common_dir")"
export BEADS_DIR="$beads_project_root/.worktree/.beads-state"
export BEADS_ACTOR="${BEADS_ACTOR:-${CODEX_THREAD_ID:+codex:$CODEX_THREAD_ID}}"
export BEADS_ACTOR="${BEADS_ACTOR:-${USER:-developer}}"
export BD_NON_INTERACTIVE=1
export BD_LAST_TOUCHED_FALLBACK=0
beads_lock="$beads_project_root/.worktree/.beads-access.lock"
beads_backup="$beads_project_root/.artifacts/beads-backup"
beads_binary="${HOME}/.local/bin/bd"
