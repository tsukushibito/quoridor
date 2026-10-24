import type { GameState, SearchResult, FullSearchResult, FullSearchOptions, Side } from './index';
export type UiMode = 'local' | 'ai';
export type UiStrategy = 'simple' | 'searchV1' | 'fullModel';
export type UiToken = { generation: number; request: number };
export type ModelIdentity = { version: 1; mainSha256: string; endingSha256: string };
export type FullModelSpec = {
  identity: ModelIdentity;
  mainBytes: number;
  endingBytes: number;
  interpretation: 'simd';
  hashLevel: 20;
  readyTimeoutMs: 30000;
  replyTimeoutMs: 1100;
  options: FullSearchOptions;
};
export type UiAction =
  | { kind: 'new' | 'setup'; mode: UiMode; humanSide: Side; strategy: UiStrategy }
  | { kind: 'resume' | 'pass' | 'retryAi' | 'save' | 'dispose' | 'cancel' }
  | { kind: 'play'; index: number }
  | { kind: 'modelFilesChanged' | 'loadModel' }
  | {
      kind: 'modelReply';
      token: UiToken;
      identity: ModelIdentity | null;
      mainBytes: number | null;
      endingBytes: number | null;
      error: string | null;
    }
  | {
      kind: 'aiPhase';
      token: UiToken;
      phase: 'initializing' | 'thinking';
      modelIdentity: ModelIdentity | null;
    }
  | { kind: 'confirm'; token: UiToken; accepted: boolean; error?: string | null }
  | { kind: 'loaded'; token: UiToken; raw: string | null; error: string | null }
  | { kind: 'written'; token: UiToken; error: string | null }
  | {
      kind: 'aiReply';
      token: UiToken;
      state: GameState;
      strategy: UiStrategy;
      move: number | null;
      searchResult: SearchResult | null;
      fullResult?: FullSearchResult | null;
      modelIdentity?: ModelIdentity | null;
      error: string | null;
    };
export type UiEffect =
  | { kind: 'cancelWorker' }
  | { kind: 'resetModel' }
  | { kind: 'forgetModel' }
  | { kind: 'loadModel'; token: UiToken; spec: FullModelSpec }
  | { kind: 'confirm'; token: UiToken; message: string }
  | { kind: 'readSave'; token: UiToken; key: string }
  | { kind: 'writeSave'; token: UiToken; key: string; raw: string }
  | {
      kind: 'think';
      token: UiToken;
      state: GameState;
      strategy: UiStrategy;
      model?: FullModelSpec;
    };
export type UiView = {
  generation: number;
  hasGame: boolean;
  mode: UiMode;
  humanSide: Side;
  strategy: UiStrategy;
  busy: boolean;
  thinking: boolean;
  aiPhase: 'idle' | 'initializing' | 'thinking';
  modelRequired: boolean;
  modelStatus: 'unloaded' | 'loading' | 'ready' | 'error';
  modelMessage: string;
  error: string;
  saveMessage: string;
  notice: string;
  title: string;
  players: string;
  score: string;
  guide: string;
  cells: {
    index: number;
    stone: number;
    legal: boolean;
    enabled: boolean;
    label: string;
    text: string;
  }[];
  passVisible: boolean;
  passDisabled: boolean;
  retryAiVisible: boolean;
  cancelVisible: boolean;
  saveDisabled: boolean;
  focusTurn: boolean;
  exitWarning: string | null;
};
export type UiOutput = { view: UiView; effects: UiEffect[] };
export type UiController = { dispatch(action: UiAction): UiOutput; free(): void };
