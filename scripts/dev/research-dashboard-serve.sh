#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 1 && "$1" == "--help" ]]; then
  printf 'Usage: research-dashboard-serve.sh [PORT]\n\nServe the generated dashboard on 127.0.0.1 (default port 8765).\nRun the generator separately; stop this foreground server with Ctrl+C.\n'
  exit 0
fi
if [[ $# -gt 1 ]]; then
  printf 'Expected at most one port (1..65535). Use --help for usage.\n' >&2
  exit 2
fi

dashboard_port="${1-8765}"
if [[ ! "$dashboard_port" =~ ^[0-9]{1,5}$ ]] || (( 10#$dashboard_port < 1 || 10#$dashboard_port > 65535 )); then
  printf 'Invalid port: %s. Expected 1..65535.\n' "$dashboard_port" >&2
  exit 2
fi
dashboard_port="$((10#$dashboard_port))"
dashboard_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
dashboard_directory="$dashboard_root/.artifacts/research-dashboard"
if [[ ! -f "$dashboard_directory/index.html" ]]; then
  printf 'Missing dashboard index.html. Generate it from %s with:\n  python3 -B scripts/dev/research-dashboard.py\n' "$dashboard_root" >&2
  exit 1
fi

printf 'Open http://127.0.0.1:%s/ (stop with Ctrl+C).\n' "$dashboard_port"
exec python3 -B -m http.server "$dashboard_port" --bind 127.0.0.1 --directory "$dashboard_directory"
