# Native inference

`InferenceBackend` consumes contiguous `[f32; 648]` rows and returns raw policy
logits `[f32; 136]` plus a bounded scalar value. Rust owns each backend exclusively;
`infer(&mut self, ...)` completes its owned stream before returning. CPU workers
can fill other requests while the runner's broker executes one independent batch.
No Python interpreter or JSON process is involved in a forward.

- `OrtBackend`: dynamically loads an explicitly selected CPU ONNX Runtime library.
  One held session, intra/inter threads1, sequential. The original Sigma model
  has fixed batch1: a multirow request is executed serially in that native session,
  **not** falsely reported as a physical CPU batch.
- `AotiBackend` (`cuda-aoti`): loads a Python-exported AOTInductor `.pt2` package.
  One CUDA stream; pinned buffers and optional CUDA Graph per encountered batch
  shape. Partial batches have their own exact shape and are never padded.
- `TensorRtBackend` (`tensorrt`): loads an FP32 TensorRT engine. It has independent
  per-shape execution contexts/buffers/graphs, owned by the Rust handle.

Both GPU backends use thin C++ ABI adapters to their vendor runtimes, not bespoke
GPU kernels. Input/model/artifact hash, shape, finite values and manifest runtime
versions are checked. Output value must be in[-1,1]. SDK exceptions become Rust
errors; initialization unwinds via RAII. Constructors refuse an unavailable device
or less than2.5GiB free VRAM (2GiB host reserve plus an initial512MiB headroom).
The runner also enforces its configured memory/deadline and output limits.

The broker owns cancellation and generation/request IDs. A CUDA call cannot be
preempted safely: it finishes, the stream is drained, then a cancelled response is
discarded. Do not free/reuse an input generation while a request is outstanding.

Build default CPU without SDK configuration:

```sh
cargo test -p quoridor-inference
```

For GPU setup, export and measured comparisons see
[`tools/model-export/README.md`](../../tools/model-export/README.md). GPU SDK
features are native-only and are absent from core/AI/Wasm dependencies.

The C headers intentionally use official ONNX Runtime API23 from release1.23.2;
installed runtime1.30 accepts that backward-compatible ABI. Header/runtime versions
are recorded separately. See `native/NOTICE.md` and the upstream license.
