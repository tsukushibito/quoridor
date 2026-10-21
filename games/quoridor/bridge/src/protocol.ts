import type { AiCorrelationDto, AiResultDto, AiStartPayloadDto, AiStatsDto, AiWorkerRequestDto,
  AiWorkerResponseDto, SearchLimitsDto } from './generated/protocol';

export const PROTOCOL_VERSION = 2;
export const ENGINE_BUILD_ID = 'quoridor-b0-1';
export const RULESET_ID = 'standard-2p-v1';
export type AiCorrelation = AiCorrelationDto;
export type SearchLimits = SearchLimitsDto;
export type AiResult = AiResultDto;
export type AiStats = AiStatsDto;
export type StartPayload = AiStartPayloadDto;
export type WorkerRequest = AiWorkerRequestDto;
export type WorkerResponse = AiWorkerResponseDto;

const record = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const uint = (v: unknown, max = 0xffff_ffff): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 && v <= max;
const key = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{42}$/.test(v);
const exact = (v: Record<string, unknown>, keys: readonly string[]): boolean => Object.keys(v).length === keys.length && keys.every(k => k in v);
export function validMeta(v: unknown): v is AiCorrelation {
  return record(v) && exact(v, ['protocolVersion', 'engineBuildId', 'requestId', 'gameEpoch', 'revision', 'positionKey', 'rulesetId', 'workerGeneration']) &&
    v.protocolVersion === PROTOCOL_VERSION && v.engineBuildId === ENGINE_BUILD_ID && uint(v.requestId) && v.requestId > 0 &&
    uint(v.gameEpoch) && v.gameEpoch > 0 && uint(v.revision) && key(v.positionKey) && v.rulesetId === RULESET_ID &&
    uint(v.workerGeneration) && v.workerGeneration > 0;
}
export function sameMeta(a: AiCorrelation, b: AiCorrelation): boolean {
  return a.protocolVersion === b.protocolVersion && a.engineBuildId === b.engineBuildId && a.requestId === b.requestId &&
    a.gameEpoch === b.gameEpoch && a.revision === b.revision && a.positionKey === b.positionKey &&
    a.rulesetId === b.rulesetId && a.workerGeneration === b.workerGeneration;
}
export function validLimits(v: unknown): v is SearchLimits {
  return record(v) && exact(v, ['simulations', 'maxNodes', 'maxDepth']) && uint(v.simulations, 4096) &&
    uint(v.maxNodes, 2048) && v.maxNodes >= 1 && uint(v.maxDepth, 48) && v.maxDepth >= 1;
}
function validSeed(v: unknown): v is string {
  if (typeof v !== 'string' || !/^(0|[1-9][0-9]{0,19})$/.test(v)) return false;
  try { return BigInt(v) <= 0xffff_ffff_ffff_ffffn; } catch { return false; }
}
function validSnapshot(v: unknown, meta: AiCorrelation): v is number[] {
  if (!Array.isArray(v) || v.length === 0 || v.length > 4096 || !v.every(byte => uint(byte, 255))) return false;
  try {
    const json: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(new Uint8Array(v)));
    return record(json) && json.schemaVersion === 1 && json.rulesetId === RULESET_ID && json.positionKey === meta.positionKey;
  } catch { return false; }
}
export function validStartPayload(v: unknown): v is StartPayload {
  return record(v) && exact(v, ['schemaVersion', 'meta', 'snapshot', 'limits', 'seed']) && v.schemaVersion === 1 &&
    validMeta(v.meta) && validSnapshot(v.snapshot, v.meta) && validLimits(v.limits) && validSeed(v.seed);
}
export function validStats(v: unknown): v is AiStats {
  return record(v) && exact(v, ['simulations', 'nodes', 'edges', 'arenaBytes', 'highWaterBytes', 'maxDepthReached', 'policyFallbacks', 'valueFallbacks', 'budgetExhausted']) &&
    uint(v.simulations, 4096) && uint(v.nodes, 2048) && uint(v.edges, 500000) && uint(v.arenaBytes, 64 * 1024 * 1024) &&
    uint(v.highWaterBytes, 64 * 1024 * 1024) && v.highWaterBytes >= v.arenaBytes && uint(v.maxDepthReached, 48) &&
    uint(v.policyFallbacks, 4096) && uint(v.valueFallbacks, 4096) && typeof v.budgetExhausted === 'boolean';
}
export function validResult(v: unknown): v is AiResult {
  return record(v) && exact(v, ['actionId', 'stats']) && (v.actionId === null || uint(v.actionId, 208)) && validStats(v.stats);
}
export function parseWorkerRequest(v: unknown): WorkerRequest | null {
  if (!record(v) || typeof v.type !== 'string') return null;
  if (v.type === 'dispose' && exact(v, ['type'])) return { type: 'dispose' };
  if (v.type === 'init' && exact(v, ['type', 'protocolVersion', 'engineBuildId', 'workerGeneration']) &&
    v.protocolVersion === PROTOCOL_VERSION && v.engineBuildId === ENGINE_BUILD_ID && uint(v.workerGeneration) && v.workerGeneration > 0)
    return v as WorkerRequest;
  if (v.type === 'start' && exact(v, ['type', 'payload']) && validStartPayload(v.payload)) return v as WorkerRequest;
  if (v.type === 'cancel' && exact(v, ['type', 'meta']) && validMeta(v.meta)) return v as WorkerRequest;
  return null;
}
export function parseWorkerResponse(v: unknown): WorkerResponse | null {
  if (!record(v) || typeof v.type !== 'string') return null;
  if (v.type === 'ready' && exact(v, ['type', 'protocolVersion', 'engineBuildId', 'workerGeneration']) &&
    uint(v.protocolVersion) && typeof v.engineBuildId === 'string' && uint(v.workerGeneration)) return v as WorkerResponse;
  if (v.type === 'cancelled' && exact(v, ['type', 'meta']) && validMeta(v.meta)) return v as WorkerResponse;
  if (v.type === 'progress' && exact(v, ['type', 'meta', 'stats', 'sliceMs']) && validMeta(v.meta) && validStats(v.stats) &&
    typeof v.sliceMs === 'number' && Number.isFinite(v.sliceMs) && v.sliceMs >= 0) return v as WorkerResponse;
  if (v.type === 'result' && exact(v, ['type', 'meta', 'result', 'sliceMs', 'sliceSamples', 'wasmMemoryBytes']) && validMeta(v.meta) && validResult(v.result) &&
    typeof v.sliceMs === 'number' && Number.isFinite(v.sliceMs) && v.sliceMs >= 0 && Array.isArray(v.sliceSamples) &&
    v.sliceSamples.length <= 4096 && v.sliceSamples.every(sample => typeof sample === 'number' && Number.isFinite(sample) && sample >= 0) &&
    uint(v.wasmMemoryBytes, 0x7fff_ffff)) return v as WorkerResponse;
  if (v.type === 'error' && exact(v, ['type', 'meta', 'code', 'message']) && (v.meta === null || validMeta(v.meta)) &&
    typeof v.code === 'string' && v.code.length <= 64 && typeof v.message === 'string' && v.message.length <= 512) return v as WorkerResponse;
  return null;
}
