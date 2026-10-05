# QF1 native evaluation

`Model::load` reads a checksum-bound binary/JSON artifact. `load_bytes` applies the
same validation to browser buffers. Models and cached accumulators are immutable;
share a model with `Arc`, retain the parent while computing a child with `delta`,
and drop the child to undo without floating point rounding drift.

QF1 has 312 sparse features per absolute player perspective. P2 rotates both axes
180 degrees. The two wall-only distances are divided by 80 and arranged STM first.
This is deliberately different from Sigma's 648-channel input canonicalization.
`encode_qf1(Position)` validates an external board. The research-only typed
`full_context`/`delta_context` accept a checked `SigmaContext` and reuse complete
wall-distance maps across pawn moves. Wall changes obtain both full maps through
`Position::wall_distance_maps`; pawn moves retain the immutable shared maps.
The cache behavior is checked in [features.rs](src/features.rs).
No global mutable evaluator or map cache is
shared by independent searches.

The legacy `QF1-f32-STM-scaled-v1` manifest remains H32/H32 with 12193 little-endian
float32 weights. The scalable `QF1-f32-STM-scaled-v2` requires `topology` with
`ft_width` and `hidden_width`, and `value_perspective: "side-to-move"`. Its layout is
row-major FT weights, FT bias, hidden weights, hidden bias, output weights, output
bias. `weights_B`, `little_endian_f32`, `weights_SHA`, `weights`, `mu_f32`, and
`sigma_f32` are explicit. Scaling values must be finite, exactly represented f32;
both sigmas must be positive. No dimensions or normalization are guessed.

Scalar f32 is the compatibility reference. `EvaluationMode::Simd` uses AVX2 at
runtime when available, and wasm simd128 when explicitly compiled with
`RUSTFLAGS='-C target-feature=+simd128'`. Products are reduced in the original order
without FMA. Otherwise it falls back to scalar. Quantization is separately selected
with `Model::quantize` and `QuantizedEvaluator`; it never silently changes a float
model. The quantized `QF1-i16-STM-scaled-v1` artifact retains topology, perspective,
per-layer scales, biases, and checksum-bound i16 weights. Dense and sparse integer
accumulations check overflow; SIMD madd pair bounds are guarded. Numeric parity
alone does not establish the quantized model's playing strength.

`cargo test -p quoridor-nnue --features research` checks native full/delta/undo
and every legal child on initial, asymmetric-wall, P2 jump, and blocked-jump
fixtures, plus scalable formats, browser byte loading, SIMD exactness, integer
roundtrips, checksum rejection, and overflow. Actual PyTorch parity is explicitly
run with its pinned interpreter:

```sh
QUORIDOR_TORCH_PYTHON=/home/vscode/.cache/inference/envs/quoridor-training/bin/python \
  cargo test -p quoridor-nnue --features research \
  actual_pytorch_float_model_matches_rust_scalable_input -- --ignored
```

The external-PyTorch test uses three inputs, one CPU thread, and no training or GPU.

For a release microbenchmark, run
`cargo run -p quoridor-nnue --features research --release --example benchmark -- synthetic 10000`,
or replace `synthetic` with a frozen float manifest. It reports warm scalar, SIMD,
and quantized evaluation and pawn-delta-plus-evaluation costs. This excludes root
feature preparation, build, initialization, game orchestration and training, so
it must not be reported as a teacher-generation speedup.
