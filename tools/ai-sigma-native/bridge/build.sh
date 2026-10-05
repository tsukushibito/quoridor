#!/usr/bin/env bash
set -euo pipefail
bridge_root="$(cd "$(dirname "$0")" && pwd)"
: "${CARGO_TARGET_DIR:?Set an explicit ignored build output directory}"
: "${CARGO_HOME:?Set the existing Cargo cache; this script does not fetch dependencies}"
exec cargo build --manifest-path "$bridge_root/Cargo.toml" --offline --locked --jobs 1 "$@"
