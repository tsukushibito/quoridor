#!/usr/bin/env bash
# Source this file in existing shells after installing without a rebuild.
export CARGO_HOME="${CARGO_HOME:-/usr/local/cargo}"
export RUSTUP_HOME="${RUSTUP_HOME:-/usr/local/rustup}"
export WASM_PACK_CACHE="${WASM_PACK_CACHE:-$CARGO_HOME/wasm-pack-cache}"
case ":$PATH:" in
  *":$CARGO_HOME/bin:"*) ;;
  *) export PATH="$CARGO_HOME/bin:$PATH" ;;
esac
export UV_CACHE_DIR="${UV_CACHE_DIR:-${INFERENCE_CACHE_DIR:-$HOME/.cache/inference}/uv}"
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-${INFERENCE_CACHE_DIR:-$HOME/.cache/inference}/python}"

export QUORIDOR_ENV_REPORT_DIR="${QUORIDOR_ENV_REPORT_DIR:-$HOME/.local/share/quoridor}"

# Suppress ORT telemetry initialization and its :memory:.ses session sidecar.
export ORT_DISABLE_TELEMETRY=1

# Main owns dependency metadata; this entry selects its own checkout source.
project_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_code_root="$(git -C "$project_script_dir" rev-parse --show-toplevel)" || {
  echo "Project code checkout is missing" >&2
  return 2 2>/dev/null || exit 2
}
export QUORIDOR_CODE_ROOT="$project_code_root"
project_common_dir="$(git -C "$project_script_dir" rev-parse --path-format=absolute --git-common-dir)"
export QUORIDOR_PROJECT_ROOT="$(dirname -- "$project_common_dir")"
project_bound_env="$(jq -er '.environments.project | select(type == "string" and startswith("/"))' "$QUORIDOR_PROJECT_ROOT/research-paths.json")" || { echo "Canonical project environment is missing" >&2; return 2 2>/dev/null || exit 2; }
[[ "${QUORIDOR_PROJECT_ENV:-$project_bound_env}" == "$project_bound_env" ]] || {
  echo "Use the canonical project environment; per-caller environments are refused" >&2
  return 2 2>/dev/null || exit 2
}
export QUORIDOR_PROJECT_ENV="$project_bound_env"
export UV_PROJECT_ENVIRONMENT="$QUORIDOR_PROJECT_ENV"
export UV_LINK_MODE=copy
export ORT_DISABLE_TELEMETRY=1

# Sourcing sets tool paths only. Repository Python execution uses this guarded
# public entry; OS/bootstrap Python is never a runtime fallback.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  [[ $# -gt 0 ]] || { echo "Usage: bash scripts/dev/project-env.sh COMMAND [ARGS...]" >&2; exit 2; }
  [[ -f "$QUORIDOR_PROJECT_ROOT/pyproject.toml" && -f "$QUORIDOR_PROJECT_ROOT/uv.lock" ]] || {
    echo "Canonical root Python project is missing" >&2; exit 2;
  }
  [[ -f "$QUORIDOR_PROJECT_ENV.setup.lock" ]] || {
    echo "Explicit project setup is required before normal execution" >&2; exit 2;
  }
  exec 9<"$QUORIDOR_PROJECT_ENV.setup.lock"
  flock --shared --nonblock 9 || { echo "Project environment writer is active" >&2; exit 2; }
  project_python="$QUORIDOR_PROJECT_ENV/bin/python"
  [[ -x "$project_python" && -f "$QUORIDOR_PROJECT_ENV/pyvenv.cfg" ]] || {
    echo "Prepared project environment is missing; run setup-project.sh explicitly" >&2; exit 2;
  }
  "$project_python" -I -c 'import os,sys,sysconfig; assert sys.version_info[:3] == (3,14,7) and not sysconfig.get_config_var("Py_GIL_DISABLED"); assert os.path.realpath(sys.prefix) == os.path.realpath(os.environ["QUORIDOR_PROJECT_ENV"]) and sys.prefix != sys.base_prefix' || {
    echo "Expected the regular Python3.14.7 project environment; no fallback" >&2; exit 2;
  }
  case "${1##*/}" in
    python*)
      [[ "$1" == python || "$1" == "$project_python" ]] || {
        echo "Use the project Python command; explicit foreign interpreters are refused" >&2; exit 2;
      }
      set -- "$project_python" "${@:2}"
      ;;
  esac
  export VIRTUAL_ENV="$QUORIDOR_PROJECT_ENV"
  [[ -f "$QUORIDOR_CODE_ROOT/games/quoridor/python/quoridor_training/__init__.py" && \
     -f "$QUORIDOR_CODE_ROOT/shared/python/quoridor_runtime/__init__.py" && \
     -f "$QUORIDOR_CODE_ROOT/shared/python/quoridor_runtime/cycle_process.py" && \
     -f "$QUORIDOR_CODE_ROOT/shared/python/quoridor_runtime/snapshot.py" ]] || {
    echo "Selected checkout Python source is missing; no Main fallback" >&2; exit 2;
  }
  export PYTHONPATH="$QUORIDOR_CODE_ROOT/games/quoridor/python:$QUORIDOR_CODE_ROOT/shared/python"
  # Exclude cwd/script-directory injection, including a caller in Main/python.
  export PYTHONSAFEPATH=1
  if [[ -n "${QUORIDOR_TENSORRT_ROOT:-}" ]]; then
    [[ "$QUORIDOR_TENSORRT_ROOT" == /* && -d "$QUORIDOR_TENSORRT_ROOT/python" ]] || {
      echo "Explicit TensorRT backend Python bindings are missing" >&2; exit 2;
    }
    export PYTHONPATH="$QUORIDOR_TENSORRT_ROOT/python:$PYTHONPATH"
  fi
  export PYTHONDONTWRITEBYTECODE=1
  exec flock --shared --nonblock "$QUORIDOR_PROJECT_ENV.setup.lock" \
    uv run --project "$QUORIDOR_PROJECT_ROOT" --locked --offline --no-sync \
    --no-python-downloads --python "$project_python" -- "$@"
fi
