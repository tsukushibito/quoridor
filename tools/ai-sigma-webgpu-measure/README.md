# WebGPU environment preflight (issue115, frame8)

`preflight.cjs` checks a real, isolated Chromium page and executes a four-element
compute sentinel. It collects adapter info, browser CDP GPU info, total physical
VRAM observations and separate browser/device/process stop receipts. It never
loads the ONNX model. SwiftShader results are software validation, not physical
GPU performance. `inspect-environment.py` checks native Vulkan availability and
published metadata for exact ORT-Web1.21.0; it does not install drivers or assets.

`runner.py` reuses the existing sole-root/subreaper ownership boundary through a
read-only import. It checks current RSS (separate from historical ru_maxrss),
allocated storage and run deadlines, and records owned PID/starttick/wait state.
Chromium can change a TID's affinity: current version repins only kernel-proven
owned TIDs and records the initial mismatch. This does not prove uninterrupted
CPU affinity between samples. The earlier exception/cleanup failure remains in
r2 evidence; it was not a GPU computation failure.

Run with a **new** run ID/config, within a currently authorized allocation:

```sh
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
SIGMA77_GIT_COMMIT=<code-commit> SIGMA77_RUN_ID=<new-run> \
python3 -B tools/ai-sigma-webgpu-measure/runner.py --config <absolute-config> \
node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot \
/workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-webgpu-measure/preflight.cjs \
--config <absolute-config>
```

The config supplies issue/frame/run ID, flags and current deadlines; old run
outputs must not be overwritten. Browser/GPU RSS guard5.5GiB and physical total
VRAM guard5.5GiB are distinct. The monitor reports VRAM read/parse failures and
stops the owned browser. Browser context teardown handles pending adapter work;
no synchronous interruption or hardware realtime is claimed.

Official references:
- https://developer.chrome.com/blog/supercharge-web-ai-testing
- https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html
- https://registry.npmjs.org/onnxruntime-web/1.21.0

Current outcome: both tested flag profiles expose SwiftShader, native Vulkan
returns VK_ERROR_INCOMPATIBLE_DRIVER. Model numeric, steady and search comparisons
are unstarted. Published ORT WebGPU asset availability is separate from this
physical-driver limitation.
