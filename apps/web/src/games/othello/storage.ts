import type { GameState, Side, Status } from '../../../../../games/othello/bridge/src';

export const SAVE_KEY = 'othello.game.v1';
export type Mode = 'local' | 'ai';
export type SavedGame = {
  version: 1;
  game: 'othello';
  mode: Mode;
  humanSide: Side;
  state: GameState;
};
export type StoragePort = Pick<Storage, 'getItem' | 'setItem'>;
export type Validator = { status(state: GameState): Promise<Status> };

export async function validateSaved(value: unknown, rules: Validator): Promise<SavedGame> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('保存形式を確認できません。');
  }
  const saved = value as SavedGame;
  const keys = Object.keys(saved).sort().join(',');
  if (
    keys !== 'game,humanSide,mode,state,version' ||
    saved.version !== 1 ||
    saved.game !== 'othello' ||
    (saved.mode !== 'local' && saved.mode !== 'ai') ||
    (saved.humanSide !== 1 && saved.humanSide !== 2)
  ) {
    throw new Error('保存のバージョン・対戦方式・担当する色を確認できません。');
  }
  // Rust validates every field of GameState, including unknown fields and all 64 cells.
  await rules.status(saved.state);
  return saved;
}

export function createRepository(storage: () => StoragePort) {
  return {
    async load(rules: Validator): Promise<SavedGame> {
      const raw = storage().getItem(SAVE_KEY);
      if (raw === null) throw new Error('保存したOthelloの対局がありません。');
      return validateSaved(JSON.parse(raw) as unknown, rules);
    },
    // Only a state confirmed by the session's Rust status call may reach this method.
    save(confirmed: SavedGame): void {
      storage().setItem(SAVE_KEY, JSON.stringify(confirmed));
    },
  };
}
export type Repository = ReturnType<typeof createRepository>;
