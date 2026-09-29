#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in ''|--update) ;; *) echo "Usage: $0 [--update]" >&2; exit 2 ;; esac
[[ $# -le 1 ]] || exit 2
bash "$script_dir/setup-rust.sh" "$@"
bash "$script_dir/verify-rust.sh"
bash "$script_dir/setup-training.sh" "$@"
bash "$script_dir/setup-beads.sh" "$@"
