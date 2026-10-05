# Fixed Sigma resident batch provider (private research scope)

`provider.py` loads original d790 ONNX initializers once and exposes JSONL on stdio. Torch uses private dynamic B=1..8; original ONNX and 174 adapter remain batch1 and unchanged. Intra/inter1, CPU0, float32, eval/inference_mode, AMP/TF32/benchmark off. CUDA is inference only. Use existing training environment with UV_OFFLINE/NO_SYNC, no install. Owning run must admit CPU/RAM/GPU/current supervisor resources and provide a hard stop; `launch.py` is the finite measurement owner, not a permanent service authorization.

Request envelope: `{op,request_id}` (string unique per request).

- `info`: modelhash, original_ONNX_batch, provider version, device, batch limits, dtype/settings, versions, cold initialization, counters and memory.
- `infer_batch`: add `backend: "cuda"|"cpuort"` and `items:[{id,features_bits648}]`. Each response item retains ID and returns `f32bits137`, `logits[136]`, `value`. CUDA executes one actual B-row forward; cpuort executes B serial batch1 forwards. Duplicate IDs/nonfinite input/out-of-range B are typed errors. Counter charges rows before each execution; cap512 per finite process, no silent label repair.
- `stop`: last info/counters; exit and wait the owned process. Generator must discard cancelled/late position responses and wait in-flight work before terminating. No auto reconnect/retry to replace a teacher label.

`broker.cjs` is one generator-parent broker, no additional spawn. Owner supplies its existing stdio request function. `infer(searchId,bits)` permits at most one pending inference per independent search. FIFO batch max2 / bounded flush target0.25ms (Node timer actual delay must be measured separately) fits current three arenas; send partial B1 rather than wait indefinitely. Broker stops queued requests and reports remaining in-flight work. It changes batching/transport only, not legal mapping, MCTS K, priors, visits, temperature or z. GPU rounding differences can still alter softmax prior/tie choices and π; finite tensor tolerance does not prove identical search paths.

Bench inputs are fixed saved five diagnostic fixtures; B8 is heterogeneous with five unique states and three explicit repeats, not eight independent game states. Raw requests/responses/IDs/output bits and costs go to compressed requests.jsonl.gz. No holdout/teacher/selfplay data is created here. Generation efficiency must subsequently be checked by 176 owner on fresh learning lineage with same model/K, after coordinator acceptance. 176 CPU generation does not wait for this provider.
