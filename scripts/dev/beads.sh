#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/beads-env.sh"
if [[ ! -x "$beads_binary" || ! -f "$BEADS_DIR/metadata.json" ]]; then
  echo 'Beads is not initialized. Run bash scripts/dev/setup-beads.sh.' >&2
  exit 1
fi
# Also serialize reads: embedded Dolt opens the store for each CLI process.
exec flock --timeout 60 "$beads_lock" "$beads_binary" --sandbox "$@"
