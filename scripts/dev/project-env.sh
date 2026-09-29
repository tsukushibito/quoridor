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
export QUORIDOR_TRAINING_ENV="${QUORIDOR_TRAINING_ENV:-${INFERENCE_CACHE_DIR:-$HOME/.cache/inference}/envs/quoridor-training}"
export QUORIDOR_ENV_REPORT_DIR="${QUORIDOR_ENV_REPORT_DIR:-$HOME/.local/share/quoridor}"
