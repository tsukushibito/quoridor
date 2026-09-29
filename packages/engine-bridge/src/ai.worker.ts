/// <reference lib="webworker" />
import init, { AiSearch, ai_engine_build_id, ai_protocol_version } from '../wasm/ai/quoridor_ai.js';
import wasmUrl from '../wasm/ai/quoridor_ai_bg.wasm?url';
import { ENGINE_BUILD_ID, PROTOCOL_VERSION, parseWorkerRequest, validMeta,
  type AiCorrelation, type AiResult, type AiStats, type WorkerResponse } from './protocol';

const scope = self as DedicatedWorkerGlobalScope;
let ready = false;
let generation = 0;
let memory: WebAssembly.Memory | null = null;
let active: { meta: AiCorrelation; search: AiSearch; timer: ReturnType<typeof setTimeout> | null;
  chunk: number; lastProgress: number; lastSlice: number; sliceSamples: number[] } | null = null;
const send = (message: WorkerResponse): void => scope.postMessage(message);
function error(meta: AiCorrelation | null, code: string, cause: unknown): void {
  send({ type: 'error', meta, code, message: String(cause).slice(0, 512) });
}
function release(): void {
  const current = active;
  active = null;
  if (!current) return;
  if (current.timer !== null) clearTimeout(current.timer);
  current.search.free();
}
function continueSearch(): void {
  const current = active;
  if (!current) return;
  current.timer = null;
  try {
    const start = performance.now();
    const done = current.search.step(current.chunk);
    const sliceMs = performance.now() - start;
    current.lastSlice = sliceMs;
    current.sliceSamples.push(sliceMs);
    if (sliceMs > 8) current.chunk = Math.max(1, Math.floor(current.chunk / 2));
    else if (sliceMs < 3) current.chunk = Math.min(16, current.chunk + 1);
    if (done) {
      const parsed: unknown = JSON.parse(current.search.finish_json());
      const result = parsed as AiResult; // The main thread validates every field before use.
      send({ type: 'result', meta: current.meta, result, sliceMs, sliceSamples: current.sliceSamples,
        wasmMemoryBytes: memory?.buffer.byteLength ?? 0 });
      release();
    } else {
      const now = performance.now();
      if (now - current.lastProgress >= 150) {
        const parsed: unknown = JSON.parse(current.search.stats_json());
        send({ type: 'progress', meta: current.meta, stats: parsed as AiStats, sliceMs });
        current.lastProgress = now;
      }
      current.timer = setTimeout(continueSearch, 0);
    }
  } catch (cause) {
    const meta = current.meta;
    release();
    error(meta, 'SEARCH_FAILED', cause);
  }
}
scope.onmessage = async (event: MessageEvent<unknown>): Promise<void> => {
  const request = parseWorkerRequest(event.data);
  if (!request) {
    const value = event.data;
    const meta = typeof value === 'object' && value !== null && 'payload' in value &&
      typeof value.payload === 'object' && value.payload !== null && 'meta' in value.payload && validMeta(value.payload.meta)
      ? value.payload.meta : null;
    error(meta, 'INVALID_REQUEST', 'Invalid AI Worker request');
    return;
  }
  if (request.type === 'dispose') { release(); ready = false; scope.close(); return; }
  if (request.type === 'init') {
    try {
      if (!ready) memory = (await init({ module_or_path: wasmUrl })).memory;
      if (ai_engine_build_id() !== ENGINE_BUILD_ID || ai_protocol_version() !== PROTOCOL_VERSION)
        throw new Error('AI Wasm build or protocol mismatch');
      generation = request.workerGeneration;
      ready = true;
      send({ type: 'ready', protocolVersion: ai_protocol_version(), engineBuildId: ai_engine_build_id(), workerGeneration: generation });
    } catch (cause) { error(null, 'STARTUP_FAILED', cause); }
    return;
  }
  if (request.type === 'cancel') {
    if (active && active.meta.workerGeneration === generation && active.meta.requestId === request.meta.requestId) {
      const meta = active.meta;
      release();
      send({ type: 'cancelled', meta });
    }
    return;
  }
  const { payload } = request;
  if (!ready || payload.meta.workerGeneration !== generation || active) {
    error(payload.meta, 'UNAVAILABLE', 'AI Worker is not ready or is busy');
    return;
  }
  try {
    const search = new AiSearch(JSON.stringify(payload));
    active = { meta: payload.meta, search, timer: null, chunk: 1, lastProgress: performance.now(), lastSlice: 0, sliceSamples: [] };
    active.timer = setTimeout(continueSearch, 0);
  } catch (cause) { error(payload.meta, 'INVALID_START', cause); }
};
