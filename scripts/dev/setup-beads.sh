#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in ''|--update) ;; *) echo "Usage: $0 [--update]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || exit 2
source "$(dirname -- "${BASH_SOURCE[0]}")/beads-env.sh"
mkdir -p "$beads_project_root/.worktree"
exec 9>"$beads_lock"
flock --timeout 60 9

if [[ ! -f "$BEADS_DIR/metadata.json" && -d "$beads_backup" ]] && \
  python3 - "$beads_backup" <<'PY'
import pathlib, sys
sys.exit(0 if any(pathlib.Path(sys.argv[1]).iterdir()) else 1)
PY
then
  echo "Database is missing but a backup exists at $beads_backup." >&2
  echo 'Preserve that backup and follow docs/development/beads-workflow.md before initializing.' >&2
  exit 1
fi

# Existing data must be backed up with the old binary before an upgrade.
if [[ -f "$BEADS_DIR/metadata.json" && -x "$beads_binary" ]]; then
  "$beads_binary" --sandbox backup init "$beads_backup"
  "$beads_binary" --sandbox backup sync
fi
if [[ -f "$BEADS_DIR/metadata.json" && ( ! -x "$beads_binary" || "${1:-}" == --update ) ]]; then
  # Preserve the complete stopped store too, including configuration, before
  # a new binary can open/migrate it (also works after container recreation).
  mkdir -p "$beads_project_root/.artifacts/beads"
  tar -czf "$beads_project_root/.artifacts/beads/pre-upgrade-$(date -u +%Y%m%dT%H%M%S).tar.gz" \
    -C "$(dirname -- "$BEADS_DIR")" "$(basename -- "$BEADS_DIR")"
fi
if [[ ! -x "$beads_binary" || "${1:-}" == --update ]]; then
  mkdir -p "$beads_project_root/.artifacts/beads"
  python3 "$beads_script_dir/install-beads.py" > "$beads_project_root/.artifacts/beads/install.json.tmp"
  mv "$beads_project_root/.artifacts/beads/install.json.tmp" "$beads_project_root/.artifacts/beads/install.json"
fi
"$beads_binary" metrics off
git -C "$beads_project_root" config --local beads.role maintainer

if [[ ! -f "$BEADS_DIR/metadata.json" ]]; then
  # Do not attach to origin, install hooks, or generate agent instructions.
  beads_init_dir="$(mktemp -d)"
  trap 'rmdir "$beads_init_dir"' EXIT
  (cd "$beads_init_dir" && "$beads_binary" --sandbox init --stealth --skip-agents --skip-hooks --non-interactive --prefix quoridor)
fi
"$beads_binary" --sandbox backup init "$beads_backup"
"$beads_binary" --sandbox info
"$beads_binary" --sandbox backup sync
"$beads_binary" version
