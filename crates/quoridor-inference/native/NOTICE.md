ONNX Runtime C headers are vendored from the official v1.23.2 tag:
https://github.com/microsoft/onnxruntime/tree/v1.23.2/include/onnxruntime/core/session

Copyright (c) Microsoft Corporation. Licensed under the MIT License. Each header
retains the upstream notice. The shim deliberately requests API23; the runtime
is loaded at execution from an explicitly configured path. Runtime1.30 accepts
this backward-compatible API. No claim is made that the header version is1.30.

LibTorch and TensorRT headers/libraries remain external framework installations;
they are not copied into this crate. Optional native features do not enter
quoridor-core, quoridor-ai or the WebAssembly product dependency tree.

Downloaded header SHA256:

- `onnxruntime_c_api.h`: `71125e66180a991d65c9bdbad4aa20daaa1f7a48c7a5c0fa5f18f250ac839a02`
- `onnxruntime_ep_c_api.h`: `b92778f50c36ecdf53d0344e0129a78b306afed653f81bba8a9597e3e6e9546f`
- `ONNXRUNTIME-LICENSE`: `2f07c72751aed99790b8a4869cf2311df85a860b22ded05fa22803587a48922c`
