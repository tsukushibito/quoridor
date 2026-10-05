# Model export and native backend verification

Model conversion happens once outside the inference hot path. The original Sigma
ONNX SHA is fixed; `folded_sigma.py` exposes the proven FP32 graph with dynamic
batch. NNUE weights use the CPU NNUE exporter/model format instead.

## Setup

Use the existing training Python; framework versions are not updated here.
`prepare-native.py` adds isolated CCCL compile headers and CUDA compatibility
symlinks. TensorRT is optional and isolated from the shared environment. Its
installer verifies package hashes, retains LinuxSM86/PTX resources by default,
and removes verified downloaded wheels. Use `--sm` for a different device.

```sh
python3 tools/model-export/prepare-native.py
/home/vscode/.cache/inference/envs/quoridor-training/bin/python \
  tools/model-export/install-tensorrt.py \
  --root /home/vscode/.cache/inference/backends/tensorrt-11.3 --sm 86
source tools/model-export/setup-native.sh
```

Current tested versions: PyTorch2.14.0+cu130, ONNX Runtime1.30, TensorRT11.3.0.99,
CUDA13 runtime, RTX3060/SM86. C++20 is required by PyTorch2.14 headers. Paths and
header/package hashes are recorded in cache manifests. No models are downloaded.

## Export and build

Explicitly bind the model and ignored artifact paths; existing outputs are rejected.
Export writes `artifact.manifest.json` with source-model/artifact hashes, shapes,
backend/runtime versions, FP32 settings and conversion time.

```sh
QUORIDOR_MODEL=.worktree/ai-sigma/models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx
QUORIDOR_EXPORT=/home/vscode/.cache/inference/rust-migration/export
/home/vscode/.cache/inference/envs/quoridor-training/bin/python \
  tools/model-export/export.py --model "$QUORIDOR_MODEL" \
  --output "$QUORIDOR_EXPORT/sigma.pt2" --backend aoti --max-batch 24
/home/vscode/.cache/inference/envs/quoridor-training/bin/python \
  tools/model-export/export.py --model "$QUORIDOR_MODEL" \
  --output "$QUORIDOR_EXPORT/sigma.engine" --backend tensorrt --max-batch 24
cargo build -p quoridor-inference --features cuda-aoti,tensorrt --release --example verify
```

TF32, AMP and cuDNN benchmarking are disabled. Dynamic batch bounds belong to the
artifact manifest. CUDA Graph creation is lazy per encountered shape; initialization
and first-forward capture are recorded separately from steady inference. No device-
wide synchronization is performed per request, only synchronization of the owned
stream before CPU output access.

## Bounded comparison

```sh
cargo run -p quoridor-inference --example fixtures > "$QUORIDOR_EXPORT/legal-inputs.json"
python3 tools/model-export/verify-native.py \
  --binary .artifacts/rust-migration/target/release/examples/verify \
  --inputs "$QUORIDOR_EXPORT/legal-inputs.json" --model "$QUORIDOR_MODEL" \
  --ort-library "$QUORIDOR_TRAINING_ROOT/lib/python3.14/site-packages/onnxruntime/capi/libonnxruntime.so.1.30.0" \
  --aoti "$QUORIDOR_EXPORT/sigma.pt2" --tensorrt "$QUORIDOR_EXPORT/sigma.engine" \
  --output /home/vscode/.cache/inference/rust-migration/verification-new
```

Use the actual ORT library path recorded for the environment if Python changes.
`fixtures` constructs24 legal-prefix/STM inputs. The verifier compares batches
1/2/3/5/6/7/8/16/24, with one first call and eight steady calls. Tolerance is
`1e-4 + 1e-4*abs(reference)`; raw outputs and stderr are retained. Measurements
include transfer, model execution, stream wait and Rust result validation.
CPU ORT serializes batch1 model calls. This is a finite backend comparison,
not a selfplay speedup or proof of identical tree choices/general model accuracy.

Recorded initial release run (fixed backend order, concurrent host compilation):

| Requests | CPU ORT | AOTI Graph | TensorRT Graph |
| --- | ---: | ---: | ---: |
| 1 | 3.696ms | 0.724ms | 1.063ms |
| 8 | 28.409ms | 1.633ms | 1.074ms |
| 24 | 87.359ms | 3.525ms | 2.736ms |

AOTI maximum absolute difference9.54e-6; TensorRT4.53e-6 across these fixtures.
AOTI export10.71s, TensorRT export8.90s after environment preparation. First
capture and loaded-library startup are excluded from the steady column but saved.
Choose the backend from complete cycle and observed batch distribution, not this
small table alone. Model outputs remain experimental artifacts under the ignored
cache; publish/adopted-model decisions are separate.
