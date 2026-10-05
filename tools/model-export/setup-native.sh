#!/usr/bin/env bash
# Source this file. No shared-environment changes or implicit downloads.
set -euo pipefail
quoridor_training_root="${QUORIDOR_TRAINING_ROOT:-/home/vscode/.cache/inference/envs/quoridor-training}"
export QUORIDOR_TRAINING_ROOT="$quoridor_training_root"
quoridor_site_root="$("$quoridor_training_root/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
export QUORIDOR_TORCH_ROOT="$quoridor_site_root/torch"
export QUORIDOR_CUDA_ROOT="$quoridor_site_root/nvidia/cu13"
export QUORIDOR_TENSORRT_ROOT="${QUORIDOR_TENSORRT_ROOT:-/home/vscode/.cache/inference/backends/tensorrt-11.3}"
export QUORIDOR_CCCL_INCLUDE="${QUORIDOR_CCCL_INCLUDE:-/home/vscode/.cache/inference/rust-migration/cccl/nvidia/cu13/include}"
export CUDA_HOME="${QUORIDOR_NATIVE_CACHE:-/home/vscode/.cache/inference/rust-migration}/cuda"
export CPLUS_INCLUDE_PATH="$quoridor_site_root/triton/backends/nvidia/include:$QUORIDOR_CCCL_INCLUDE${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
export PYTHONPATH="$QUORIDOR_TENSORRT_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-.artifacts/rust-migration/target}"
export LD_LIBRARY_PATH="$QUORIDOR_TORCH_ROOT/lib:$QUORIDOR_CUDA_ROOT/lib:$QUORIDOR_TENSORRT_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-/home/vscode/.cache/inference/rust-migration/torchinductor}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-/home/vscode/.cache/inference/rust-migration/triton}"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
