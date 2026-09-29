import { ENGINE_BUILD_ID, PROTOCOL_VERSION, RULESET_ID, parseWorkerResponse, sameMeta, validMeta,
  validStartPayload, type AiCorrelation, type AiResult, type AiStats, type SearchLimits, type StartPayload } from './protocol';

export interface SearchContext {
  gameEpoch: number; revision: number; positionKey: string; snapshot: Uint8Array;
  limits: SearchLimits; seed: string; onProgress?: (stats: AiStats, sliceMs: number) => void;
}
type Pending = { meta: AiCorrelation; resolve: (result: AiResult) => void; reject: (error: Error) => void;
  onProgress: ((stats: AiStats, sliceMs: number) => void) | undefined; timeout: ReturnType<typeof setTimeout> };
type Ready = { promise: Promise<void>; resolve: () => void; reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout> };
const invalidated = (): Error => new Error('AI request invalidated');

export class AiClient {
  private worker: Worker | null = null;
  private generation = 0;
  private nextId = 0;
  private pending: Pending | null = null;
  private ready: Ready | null = null;
  private initialized = false;
  private disposed = false;
  private cancelWait: Promise<void> | null = null;
  private cancelDone: (() => void) | null = null;
  private cancelMeta: AiCorrelation | null = null;
  private cancelTimer: ReturnType<typeof setTimeout> | null = null;
  private sliceSamples: number[] = [];
  private cancelledLatencies: number[] = [];
  private lastHighWater = 0;
  private lastWasmMemory = 0;
  private requestEpoch = 0;
  constructor(private readonly createWorker: () => Worker = () => new Worker(new URL('./ai.worker.ts', import.meta.url), { type: 'module' })) {}
  get workerGeneration(): number { return this.generation; }
  get isReady(): boolean { return this.initialized; }
  diagnostics(): { slices: number[]; cancellationMs: number[]; highWaterBytes: number; wasmMemoryBytes: number } {
    return { slices: [...this.sliceSamples], cancellationMs: [...this.cancelledLatencies],
      highWaterBytes: this.lastHighWater, wasmMemoryBytes: this.lastWasmMemory };
  }
  private settlePending(error: Error): void {
    const pending = this.pending;
    this.pending = null;
    if (pending) { clearTimeout(pending.timeout); pending.reject(error); }
  }
  private finishCancel(): void {
    if (this.cancelTimer !== null) clearTimeout(this.cancelTimer);
    this.cancelTimer = null;
    this.cancelMeta = null;
    this.cancelDone?.();
    this.cancelDone = null;
    this.cancelWait = null;
  }
  private stop(error: Error, final: boolean): void {
    const worker = this.worker;
    this.worker = null;
    this.initialized = false;
    ++this.generation;
    this.settlePending(error);
    if (this.ready) { clearTimeout(this.ready.timeout); this.ready.reject(error); this.ready = null; }
    this.finishCancel();
    if (worker) { try { worker.postMessage({ type: 'dispose' }); } catch { /* already broken */ } worker.terminate(); }
    if (final) this.disposed = true;
  }
  private onMessage(data: unknown, generation: number): void {
    if (generation !== this.generation) return;
    const message = parseWorkerResponse(data);
    if (!message) {
      // A malformed response for this request is a bounded failure; unrelated noise is ignored.
      const meta = typeof data === 'object' && data !== null && 'meta' in data ? data.meta : null;
      const current = this.pending?.meta;
      const matches = current && ((validMeta(meta) && sameMeta(meta, current)) ||
        (typeof meta === 'object' && meta !== null && 'requestId' in meta && 'workerGeneration' in meta &&
          meta.requestId === current.requestId && meta.workerGeneration === current.workerGeneration));
      if (matches) this.stop(new Error('Invalid AI Worker response'), false);
      return;
    }
    if (message.type === 'ready') {
      if (!this.ready) return;
      if (message.protocolVersion !== PROTOCOL_VERSION || message.engineBuildId !== ENGINE_BUILD_ID || message.workerGeneration !== generation) {
        this.stop(new Error('AI Worker build mismatch'), false); return;
      }
      clearTimeout(this.ready.timeout);
      this.initialized = true;
      this.ready.resolve();
      this.ready = null;
      return;
    }
    if (message.type === 'cancelled') {
      if (this.cancelMeta && sameMeta(message.meta, this.cancelMeta)) this.finishCancel();
      return;
    }
    if (message.type === 'error') {
      if (message.meta === null) {
        if (this.ready) this.stop(new Error(message.message), false);
      } else if (this.pending && sameMeta(message.meta, this.pending.meta)) this.settlePending(new Error(`${message.code}: ${message.message}`));
      return;
    }
    const pending = this.pending;
    if (!pending || !sameMeta(message.meta, pending.meta)) return;
    if (message.type === 'progress') {
      this.lastHighWater = Math.max(this.lastHighWater, message.stats.highWaterBytes);
      pending.onProgress?.(message.stats, message.sliceMs);
    } else {
      this.sliceSamples.push(...message.sliceSamples);
      if (this.sliceSamples.length > 10000) this.sliceSamples.splice(0, this.sliceSamples.length - 10000);
      this.lastHighWater = Math.max(this.lastHighWater, message.result.stats.highWaterBytes);
      this.lastWasmMemory = Math.max(this.lastWasmMemory, message.wasmMemoryBytes);
      this.pending = null;
      clearTimeout(pending.timeout);
      pending.resolve(message.result);
    }
  }
  startWorker(): Promise<void> {
    if (this.disposed) return Promise.reject(new Error('AI client disposed'));
    if (this.initialized) return Promise.resolve();
    if (this.ready) return this.ready.promise;
    let worker: Worker;
    try { worker = this.createWorker(); } catch (error) { return Promise.reject(error instanceof Error ? error : new Error(String(error))); }
    this.worker = worker;
    const generation = ++this.generation;
    let resolve!: () => void;
    let reject!: (error: Error) => void;
    const promise = new Promise<void>((yes, no) => { resolve = yes; reject = no; });
    const timeout = setTimeout(() => this.stop(new Error('AI Worker startup timed out'), false), 8000);
    this.ready = { promise, resolve, reject, timeout };
    worker.onmessage = event => this.onMessage(event.data as unknown, generation);
    worker.onerror = event => { event.preventDefault(); if (generation === this.generation) this.stop(new Error(event.message || 'AI Worker failed'), false); };
    worker.onmessageerror = () => { if (generation === this.generation) this.stop(new Error('AI Worker message error'), false); };
    try { worker.postMessage({ type: 'init', protocolVersion: PROTOCOL_VERSION, engineBuildId: ENGINE_BUILD_ID, workerGeneration: generation }); }
    catch (error) { this.stop(error instanceof Error ? error : new Error(String(error)), false); }
    return promise;
  }
  async search(context: SearchContext): Promise<AiResult> {
    if (this.disposed) throw new Error('AI client disposed');
    const requestEpoch = this.requestEpoch;
    if (this.cancelWait) await this.cancelWait;
    if (requestEpoch !== this.requestEpoch) throw invalidated();
    await this.startWorker();
    if (requestEpoch !== this.requestEpoch) throw invalidated();
    if (!this.worker || this.pending || !this.initialized) throw new Error('AI Worker unavailable or busy');
    const meta: AiCorrelation = { protocolVersion: PROTOCOL_VERSION, engineBuildId: ENGINE_BUILD_ID,
      requestId: ++this.nextId, gameEpoch: context.gameEpoch, revision: context.revision,
      positionKey: context.positionKey, rulesetId: RULESET_ID, workerGeneration: this.generation };
    const payload: StartPayload = { schemaVersion: 1, meta, snapshot: Array.from(context.snapshot), limits: context.limits, seed: context.seed };
    if (!validStartPayload(payload)) throw new Error('Invalid AI search request');
    return new Promise<AiResult>((resolve, reject) => {
      const timeout = setTimeout(() => { this.settlePending(new Error('AI search timed out')); this.stop(new Error('AI search timed out'), false); }, 45000);
      this.pending = { meta, resolve, reject, onProgress: context.onProgress, timeout };
      try { this.worker!.postMessage({ type: 'start', payload }); }
      catch (error) { this.stop(error instanceof Error ? error : new Error(String(error)), false); }
    });
  }
  cancel(): void {
    ++this.requestEpoch;
    const pending = this.pending;
    if (!pending || !this.worker) return;
    this.settlePending(invalidated());
    const start = performance.now();
    this.cancelMeta = pending.meta;
    this.cancelWait = new Promise<void>(resolve => { this.cancelDone = resolve; });
    const worker = this.worker;
    try { worker.postMessage({ type: 'cancel', meta: pending.meta }); }
    catch { this.stop(new Error('AI Worker cancellation failed'), false); return; }
    this.cancelTimer = setTimeout(() => {
      this.stop(new Error('AI Worker cancel acknowledgement timed out'), false);
    }, 250);
    const done = this.cancelDone;
    this.cancelDone = () => { this.cancelledLatencies.push(performance.now() - start); done?.(); };
  }
  restart(): Promise<void> { ++this.requestEpoch; this.stop(invalidated(), false); return this.startWorker(); }
  dispose(): void { if (!this.disposed) { ++this.requestEpoch; this.stop(invalidated(), true); } }
}
