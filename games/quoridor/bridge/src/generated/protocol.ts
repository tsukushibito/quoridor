// Generated from quoridor-wasm/src/wire.rs. Do not edit by hand.
export type NewGameConfigDto = { firstPlayer: number, wallsPerPlayer: number, humanPlayer: number, };

export type GameViewDto = { schemaVersion: number, rulesetId: string, pawns: [number, number], wallsRemaining: [number, number], horizontalWalls: Array<number>, verticalWalls: Array<number>, turn: number, winner: number | null, ply: number, legalMask: Array<number>, positionKey: string, };

export type ReplayDto = { schemaVersion: number, rulesetId: string, initialConfig: NewGameConfigDto, actions: Array<number>, ply: number, positionKey: string, };

export type SnapshotDto = { schemaVersion: number, rulesetId: string, pawns: [number, number], wallsRemaining: [number, number], horizontalWalls: Array<number>, verticalWalls: Array<number>, turn: number, winner: number | null, ply: number, positionKey: string, };

export type AiCorrelationDto = { protocolVersion: number, engineBuildId: string, requestId: number, gameEpoch: number, revision: number, positionKey: string, rulesetId: string, workerGeneration: number, };

export type SearchLimitsDto = { simulations: number, maxNodes: number, maxDepth: number, };

export type AiStartPayloadDto = { schemaVersion: number, meta: AiCorrelationDto, snapshot: Array<number>, limits: SearchLimitsDto, seed: string, };

export type AiStatsDto = { simulations: number, nodes: number, edges: number, arenaBytes: number, highWaterBytes: number, maxDepthReached: number, policyFallbacks: number, valueFallbacks: number, budgetExhausted: boolean, };

export type AiResultDto = { actionId: number | null, stats: AiStatsDto, };

export type AiWorkerRequestDto = { "type": "init", protocolVersion: number, engineBuildId: string, workerGeneration: number, } | { "type": "start", payload: AiStartPayloadDto, } | { "type": "cancel", meta: AiCorrelationDto, } | { "type": "dispose" };

export type AiWorkerResponseDto = { "type": "ready", protocolVersion: number, engineBuildId: string, workerGeneration: number, } | { "type": "progress", meta: AiCorrelationDto, stats: AiStatsDto, sliceMs: number, } | { "type": "result", meta: AiCorrelationDto, result: AiResultDto, sliceMs: number, sliceSamples: Array<number>, wasmMemoryBytes: number, } | { "type": "cancelled", meta: AiCorrelationDto, } | { "type": "error", meta: AiCorrelationDto | null, code: string, message: string, };
