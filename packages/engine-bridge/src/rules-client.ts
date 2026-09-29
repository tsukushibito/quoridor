import init, { RulesGame, validate_search_snapshot } from '../wasm/rules/quoridor_rules.js';
import wasmUrl from '../wasm/rules/quoridor_rules_bg.wasm?url';
import type { GameViewDto, NewGameConfigDto, ReplayDto } from './generated/protocol';

export type GameView = GameViewDto;
export type SavedGame = ReplayDto;
export type NewGameConfig = NewGameConfigDto;
export class RulesBridgeError extends Error {
  constructor(readonly code: string) { super(`Rules engine: ${code}`); this.name = 'RulesBridgeError'; }
}
const codes = new Set(['OUT_OF_RANGE', 'ILLEGAL_ACTION', 'GAME_OVER', 'INVALID_POSITION',
  'INVALID_UNDO', 'INVALID_REPLAY', 'INVALID_SNAPSHOT', 'INPUT_TOO_LARGE', 'INVALID_VIEW', 'INVALID_JSON', 'INVALID_CONFIG']);
function bridgeError(error: unknown): RulesBridgeError {
  if (error instanceof RulesBridgeError) return error;
  const text = String(error);
  const code = [...codes].find(item => text.includes(item)) ?? 'WASM_ERROR';
  return new RulesBridgeError(code);
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function integer(value: unknown, minimum: number, maximum: number): value is number {
  return Number.isInteger(value) && typeof value === 'number' && value >= minimum && value <= maximum;
}
function tuple2(value: unknown, minimum: number, maximum: number): value is [number, number] {
  return Array.isArray(value) && value.length === 2 && value.every(item => integer(item, minimum, maximum));
}
function walls(value: unknown): value is number[] {
  return Array.isArray(value) && value.length <= 20 && value.every(item => integer(item, 0, 63)) &&
    new Set(value).size === value.length;
}
function validKey(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{42}$/.test(value);
}
export function validateGameView(value: unknown): GameView {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.rulesetId !== 'standard-2p-v1' ||
    !tuple2(value.pawns, 0, 80) || value.pawns[0] === value.pawns[1] ||
    !tuple2(value.wallsRemaining, 0, 10) || !walls(value.horizontalWalls) || !walls(value.verticalWalls) ||
    !integer(value.turn, 0, 1) || !(value.winner === null || integer(value.winner, 0, 1)) ||
    !integer(value.ply, 0, 0xffff_ffff) || !validKey(value.positionKey) ||
    !Array.isArray(value.legalMask) || value.legalMask.length !== 209 ||
    !value.legalMask.every(item => item === 0 || item === 1)) {
    throw new RulesBridgeError('INVALID_VIEW');
  }
  return value as GameView;
}
function validateConfig(value: unknown): NewGameConfig {
  if (!isRecord(value) || value.firstPlayer !== 0 || value.wallsPerPlayer !== 10 ||
    !integer(value.humanPlayer, 0, 1) || Object.keys(value).length !== 3) {
    throw new RulesBridgeError('INVALID_CONFIG');
  }
  return value as NewGameConfig;
}
export function validateReplayShape(value: unknown): SavedGame {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.rulesetId !== 'standard-2p-v1' ||
    !isRecord(value.initialConfig) || Object.keys(value.initialConfig).length !== 3 ||
    !Array.isArray(value.actions) || value.actions.length > 4096 ||
    !value.actions.every(item => integer(item, 0, 208)) ||
    !integer(value.ply, 0, 4096) || value.ply !== value.actions.length ||
    !validKey(value.positionKey) || Object.keys(value).length !== 6) {
    throw new RulesBridgeError('INVALID_REPLAY');
  }
  try { validateConfig(value.initialConfig); }
  catch { throw new RulesBridgeError('INVALID_REPLAY'); }
  return value as SavedGame;
}
function decodeJson(text: string): unknown {
  try { return JSON.parse(text) as unknown; } catch { throw new RulesBridgeError('INVALID_JSON'); }
}
async function initRules(): Promise<void> { await init({ module_or_path: wasmUrl }); }

export class RulesClient {
  private constructor(private wasm: RulesGame | null) {}
  static async createGame(config: NewGameConfig = { firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: 0 }): Promise<RulesClient> {
    validateConfig(config);
    await initRules();
    try { return new RulesClient(new RulesGame(JSON.stringify(config))); }
    catch (error) { throw bridgeError(error); }
  }
  private instance(): RulesGame {
    if (!this.wasm) throw new RulesBridgeError('DISPOSED');
    return this.wasm;
  }
  getView(): GameView {
    try { return validateGameView(decodeJson(this.instance().get_view())); }
    catch (error) { throw bridgeError(error); }
  }
  applyAction(actionId: number): GameView {
    const wasm = this.instance();
    if (!integer(actionId, 0, 208)) throw new RulesBridgeError('OUT_OF_RANGE');
    try { return validateGameView(decodeJson(wasm.apply_action(JSON.stringify(actionId)))); }
    catch (error) { throw bridgeError(error); }
  }
  undoToPly(ply: number): GameView {
    const wasm = this.instance();
    if (!integer(ply, 0, 0xffff_ffff)) throw new RulesBridgeError('INVALID_UNDO');
    try { return validateGameView(decodeJson(wasm.undo_to_ply(JSON.stringify(ply)))); }
    catch (error) { throw bridgeError(error); }
  }
  exportSearchSnapshot(): Uint8Array {
    try { return new Uint8Array(this.instance().export_search_snapshot()); }
    catch (error) { throw bridgeError(error); }
  }
  static validateSearchSnapshot(bytes: Uint8Array): string {
    if (!(bytes instanceof Uint8Array)) throw new RulesBridgeError('INVALID_SNAPSHOT');
    try { return validate_search_snapshot(new Uint8Array(bytes)); }
    catch (error) { throw bridgeError(error); }
  }
  exportReplay(): SavedGame {
    try { return validateReplayShape(decodeJson(this.instance().export_replay())); }
    catch (error) { throw bridgeError(error); }
  }
  importReplay(save: unknown): GameView {
    const wasm = this.instance();
    const checked = validateReplayShape(save);
    try { return validateGameView(decodeJson(wasm.import_replay(JSON.stringify(checked)))); }
    catch (error) { throw bridgeError(error); }
  }
  dispose(): void {
    this.wasm?.free();
    this.wasm = null;
  }
}

export interface InitialPosition {
  rulesetId: 'standard-2p-v1'; pawns: [[number, number], [number, number]];
  wallsRemaining: [number, number]; turn: 0;
}
export async function loadInitialPosition(): Promise<InitialPosition> {
  const client = await RulesClient.createGame();
  try {
    const view = client.getView();
    return { rulesetId: 'standard-2p-v1', pawns: [[view.pawns[0] % 9, Math.floor(view.pawns[0] / 9)],
      [view.pawns[1] % 9, Math.floor(view.pawns[1] / 9)]],
    wallsRemaining: [view.wallsRemaining[0], view.wallsRemaining[1]], turn: 0 };
  } finally { client.dispose(); }
}
export { wasmUrl as rulesWasmUrl };
