import { validateReplayShape, type SavedGame } from '@quoridor/engine-bridge';
import type { MatchMode } from '../session/session-controller';

export const GAME_KEY = 'quoridor.m1.game.v1';
export const SETTINGS_KEY = 'quoridor.m1.settings.v1';
export const MAX_GAME_CHARS = 70_000;
const MAX_SETTINGS_CHARS = 1_024;
const RULESET = 'standard-2p-v1';

export type MatchOptions = Readonly<{ mode: MatchMode; humanSide: 0 | 1; simulations: number }>;
export type SavedMatch = Readonly<{ schemaVersion: 1; rulesetId: typeof RULESET; match: MatchOptions; replay: SavedGame }>;
export type LocalSettings = Readonly<{ schemaVersion: 1; nextMatch: MatchOptions; reducedMotion: boolean }>;
export const DEFAULT_SETTINGS: LocalSettings = { schemaVersion: 1,
  nextMatch: { mode: 'pvp', humanSide: 0, simulations: 96 }, reducedMotion: false };

export type ReadResult<T> = { status: 'ok'; value: T } | { status: 'empty' } |
  { status: 'invalid'; reason: string } | { status: 'unavailable' };
export type WriteResult = { status: 'ok' } | { status: 'unavailable' | 'quota' | 'failed' };
export type StoragePort = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function keys(value: Record<string, unknown>, expected: string[]): boolean {
  return Object.keys(value).length === expected.length && expected.every(key => Object.hasOwn(value, key));
}
function matchOptions(value: unknown): MatchOptions | null {
  if (!record(value) || !keys(value, ['mode', 'humanSide', 'simulations']) ||
    (value.mode !== 'pvp' && value.mode !== 'ai') || (value.humanSide !== 0 && value.humanSide !== 1) ||
    typeof value.simulations !== 'number' || !Number.isInteger(value.simulations) ||
    value.simulations < 0 || value.simulations > 4096) return null;
  return { mode: value.mode, humanSide: value.humanSide, simulations: value.simulations };
}
export function validateMatchOptions(value: unknown): MatchOptions {
  const options = matchOptions(value);
  if (!options) throw new Error('Invalid match options');
  return options;
}
export function validateSavedMatch(value: unknown): SavedMatch {
  if (!record(value) || !keys(value, ['schemaVersion', 'rulesetId', 'match', 'replay']) ||
    value.schemaVersion !== 1 || value.rulesetId !== RULESET) throw new Error('Unknown saved game format');
  const match = validateMatchOptions(value.match);
  let replay: SavedGame;
  try { replay = validateReplayShape(value.replay); } catch { throw new Error('Invalid saved replay'); }
  if (replay.rulesetId !== RULESET || replay.initialConfig.humanPlayer !== match.humanSide)
    throw new Error('Saved player assignment differs from replay');
  return { schemaVersion: 1, rulesetId: RULESET, match, replay };
}
export function validateSettings(value: unknown): LocalSettings {
  if (!record(value) || !keys(value, ['schemaVersion', 'nextMatch', 'reducedMotion']) ||
    value.schemaVersion !== 1 || typeof value.reducedMotion !== 'boolean') throw new Error('Invalid settings format');
  const nextMatch = validateMatchOptions(value.nextMatch);
  if (![48, 96, 192, 4096].includes(nextMatch.simulations)) throw new Error('Unsupported setting budget');
  return { schemaVersion: 1, nextMatch, reducedMotion: value.reducedMotion };
}
export function makeSavedMatch(replay: SavedGame, match: MatchOptions): SavedMatch {
  return validateSavedMatch({ schemaVersion: 1, rulesetId: RULESET, replay, match });
}
function writeFailure(error: unknown): WriteResult {
  return { status: error instanceof DOMException && error.name === 'QuotaExceededError' ? 'quota' : 'failed' };
}
export class LocalStateRepository {
  constructor(private readonly storage: () => StoragePort = () => window.localStorage) {}
  private read<T>(key: string, limit: number, validate: (value: unknown) => T): ReadResult<T> {
    let raw: string | null;
    try { raw = this.storage().getItem(key); } catch { return { status: 'unavailable' }; }
    if (raw === null) return { status: 'empty' };
    if (raw.length > limit) return { status: 'invalid', reason: 'Stored data exceeds the size limit' };
    try { return { status: 'ok', value: validate(JSON.parse(raw) as unknown) }; }
    catch (error) { return { status: 'invalid', reason: error instanceof Error ? error.message : String(error) }; }
  }
  readGame(): ReadResult<SavedMatch> { return this.read(GAME_KEY, MAX_GAME_CHARS, validateSavedMatch); }
  readSettings(): ReadResult<LocalSettings> { return this.read(SETTINGS_KEY, MAX_SETTINGS_CHARS, validateSettings); }
  private write(key: string, value: unknown, limit: number): WriteResult {
    let raw: string;
    try { raw = JSON.stringify(value); } catch { return { status: 'failed' }; }
    if (raw.length > limit) return { status: 'failed' };
    let storage: StoragePort;
    try { storage = this.storage(); } catch { return { status: 'unavailable' }; }
    try { storage.setItem(key, raw); return { status: 'ok' }; }
    catch (error) { return writeFailure(error); }
  }
  writeGame(value: SavedMatch): WriteResult {
    try { return this.write(GAME_KEY, validateSavedMatch(value), MAX_GAME_CHARS); }
    catch { return { status: 'failed' }; }
  }
  writeSettings(value: LocalSettings): WriteResult {
    try { return this.write(SETTINGS_KEY, validateSettings(value), MAX_SETTINGS_CHARS); }
    catch { return { status: 'failed' }; }
  }
  clearGame(): WriteResult {
    let storage: StoragePort;
    try { storage = this.storage(); } catch { return { status: 'unavailable' }; }
    try { storage.removeItem(GAME_KEY); return { status: 'ok' }; }
    catch (error) { return writeFailure(error); }
  }
}
