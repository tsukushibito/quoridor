import type { GameState, Side, Status } from '../../../../../games/othello/bridge/src';
import type { AIClient } from './ai-client';
import type { Mode, Repository, SavedGame } from './storage';

export type Rules = {
  newGame(): Promise<GameState>;
  play(state: GameState, index: number): Promise<GameState>;
  pass(state: GameState): Promise<GameState>;
  status(state: GameState): Promise<Status>;
};
export type SessionView = {
  game: SavedGame | undefined;
  status: Status | undefined;
  busy: boolean;
  thinking: boolean;
  error: string;
  saveMessage: string;
  notice: string;
};
export function createSession(ports: {
  rules: Rules;
  repository: Repository;
  ai: AIClient;
  changed(view: SessionView): void;
}) {
  const view: SessionView = {
    game: undefined,
    status: undefined,
    busy: false,
    thinking: false,
    error: '',
    saveMessage: '',
    notice: '',
  };
  let generation = 0;
  let disposed = false;
  let preserveSaved = false;
  let exitWarning: string | undefined;
  const current = (token: number) => !disposed && token === generation;
  const emit = () => {
    if (!disposed) ports.changed({ ...view });
  };
  const detail = (error: unknown) => (error instanceof Error ? error.message : String(error));
  function save(): void {
    if (!view.game) return;
    if (preserveSaved) {
      exitWarning =
        'Othelloの元の保存を保持しています。続きから再試行するか、新しい対局を選んでください。';
      view.saveMessage = exitWarning;
      return;
    }
    try {
      ports.repository.save(view.game);
      exitWarning = undefined;
      view.saveMessage = 'この端末に保存しました。';
    } catch (error) {
      exitWarning = `Othelloを保存できませんでした。${detail(error)}`;
      view.saveMessage = exitWarning;
    }
  }
  function begin(): number {
    const token = ++generation;
    ports.ai.cancel();
    view.busy = true;
    view.thinking = false;
    view.error = '';
    emit();
    return token;
  }
  function fail(error: unknown, token: number): void {
    if (!current(token)) return;
    view.busy = false;
    view.thinking = false;
    view.error = detail(error);
    emit();
  }
  async function confirm(
    game: SavedGame,
    token: number,
    notice: string,
    replaceSave = false,
  ): Promise<void> {
    const status = await ports.rules.status(game.state);
    if (!current(token)) return;
    if (replaceSave) preserveSaved = false;
    view.game = game;
    view.status = status;
    view.notice = notice;
    view.busy = false;
    view.thinking = false;
    save();
    emit();
    void think(token);
  }
  async function think(token: number): Promise<void> {
    const game = view.game;
    const status = view.status;
    if (
      !current(token) ||
      !game ||
      !status ||
      status.terminal ||
      game.mode !== 'ai' ||
      game.state.toMove === game.humanSide
    )
      return;
    view.busy = true;
    view.thinking = true;
    emit();
    try {
      let state: GameState;
      let notice: string;
      if (status.mustPass) {
        state = await ports.rules.pass(game.state);
        notice = '簡易AIは合法手がないためパスしました。';
      } else {
        const move = await ports.ai.choose(game.state);
        if (!current(token)) return;
        if (move === null) throw new Error('AIが手を返しませんでした。再試行できます。');
        state = await ports.rules.play(game.state, move);
        notice = `簡易AIが ${String.fromCharCode(65 + (move % 8))}${Math.floor(move / 8) + 1} に置きました。`;
      }
      if (!current(token)) return;
      ports.ai.cancel();
      await confirm({ ...game, state }, token, notice);
    } catch (error) {
      if (current(token)) ports.ai.cancel();
      fail(error, token);
    }
  }
  const session = {
    async start(mode: Mode, humanSide: Side): Promise<void> {
      if (disposed || (mode !== 'local' && mode !== 'ai') || (humanSide !== 1 && humanSide !== 2))
        return;
      const token = begin();
      try {
        const state = await ports.rules.newGame();
        if (!current(token)) return;
        await confirm(
          { version: 1, game: 'othello', mode, humanSide, state },
          token,
          '新しい対局です。黒から始めます。',
          true,
        );
      } catch (error) {
        fail(error, token);
      }
    },
    async resume(): Promise<void> {
      if (disposed) return;
      // A pending/failed read must not let teardown overwrite an unreadable slot
      // with the older match still displayed. Only validated resume or explicit new replaces it.
      preserveSaved = true;
      const token = begin();
      try {
        const saved = await ports.repository.load(ports.rules);
        if (!current(token)) return;
        await confirm(saved, token, '保存した対局を再開しました。', true);
      } catch (error) {
        fail(error, token);
      }
    },
    async play(index: number): Promise<void> {
      const game = view.game;
      const status = view.status;
      if (
        disposed ||
        view.busy ||
        !game ||
        !status ||
        status.terminal ||
        status.mustPass ||
        !status.legalMoves.includes(index) ||
        (game.mode === 'ai' && game.state.toMove !== game.humanSide)
      )
        return;
      const token = begin();
      try {
        const state = await ports.rules.play(game.state, index);
        if (!current(token)) return;
        await confirm(
          { ...game, state },
          token,
          `${String.fromCharCode(65 + (index % 8))}${Math.floor(index / 8) + 1} に置きました。`,
        );
      } catch (error) {
        fail(error, token);
      }
    },
    async pass(): Promise<void> {
      const game = view.game;
      if (
        disposed ||
        view.busy ||
        !game ||
        !view.status?.mustPass ||
        (game.mode === 'ai' && game.state.toMove !== game.humanSide)
      )
        return;
      const token = begin();
      try {
        const state = await ports.rules.pass(game.state);
        if (!current(token)) return;
        await confirm(
          { ...game, state },
          token,
          `${game.state.toMove === 1 ? '黒' : '白'}は合法手がないためパスしました。`,
        );
      } catch (error) {
        fail(error, token);
      }
    },
    retryAI(): void {
      if (disposed || view.busy) return;
      const token = ++generation;
      view.error = '';
      void think(token);
    },
    save(): void {
      if (!disposed) {
        save();
        emit();
      }
    },
    dispose(): void {
      if (disposed) return;
      // Save only the last Rust-confirmed state, never an in-flight result.
      save();
      disposed = true;
      generation++;
      ports.ai.cancel();
    },
    exitWarning: () => exitWarning,
  };
  emit();
  return session;
}
export type Session = ReturnType<typeof createSession>;
