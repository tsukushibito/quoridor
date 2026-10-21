import type { GameState, SearchResult, Side } from './index';
export type UiMode = 'local' | 'ai';
export type UiStrategy = 'simple' | 'searchV1';
export type UiToken = { generation: number; request: number };
export type UiAction =
  | { kind: 'new' | 'setup'; mode: UiMode; humanSide: Side; strategy: UiStrategy }
  | { kind: 'resume' | 'pass' | 'retryAi' | 'save' | 'dispose' | 'cancel' }
  | { kind: 'play'; index: number }
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
      error: string | null;
    };
export type UiEffect =
  | { kind: 'cancelWorker' }
  | { kind: 'confirm'; token: UiToken; message: string }
  | { kind: 'readSave'; token: UiToken; key: string }
  | { kind: 'writeSave'; token: UiToken; key: string; raw: string }
  | { kind: 'think'; token: UiToken; state: GameState; strategy: UiStrategy };
export type UiView = {
  generation: number;
  hasGame: boolean;
  mode: UiMode;
  humanSide: Side;
  strategy: UiStrategy;
  busy: boolean;
  thinking: boolean;
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
