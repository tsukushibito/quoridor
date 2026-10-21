// No Wasm import or initialization runs until an exported operation is requested.
import type { UiController } from './ui';
export type { UiAction, UiController, UiEffect, UiMode, UiOutput, UiToken, UiView } from './ui';
export type Side = 1 | 2;
type Row = [number, number, number, number, number, number, number, number];
export type Board = [...Row, ...Row, ...Row, ...Row, ...Row, ...Row, ...Row, ...Row];
export type GameState = { version: 1; board: Board; toMove: Side };
export type Status = {
  black: number;
  white: number;
  legalMoves: number[];
  mustPass: boolean;
  terminal: boolean;
  winner: Side | null;
};

export type SearchOptions = {
  timeMs?: number;
  ttMiB?: number;
  maxDepth?: number;
  exactEmpties?: number;
};
export type SearchResult = {
  move: number | null;
  score: number;
  scoreKind: 'heuristic' | 'discDifference';
  completedDepth: number;
  nodes: number;
  elapsedMs: number;
  timedOut: boolean;
  cancelled: boolean;
  proven: boolean;
};
export type EvaluationResult = { score: number; scoreKind: 'heuristic'; proven: false };
export type PatternEvaluator = {
  readonly kind: 'patternV1';
  evaluate(state: GameState): EvaluationResult;
  search(state: GameState, options?: SearchOptions): SearchResult;
  free(): void;
};

type Wasm = typeof import('../wasm/othello.js');
let loaded: Promise<Wasm> | undefined;

function load(): Promise<Wasm> {
  if (!loaded) {
    loaded = (async () => {
      const [wasm, url] = await Promise.all([
        import('../wasm/othello.js'),
        import('../wasm/othello_bg.wasm?url'),
      ]);
      await wasm.default({ module_or_path: url.default });
      return wasm;
    })().catch((error: unknown) => {
      loaded = undefined;
      throw error;
    });
  }
  return loaded;
}

export async function newGame(): Promise<GameState> {
  return JSON.parse((await load()).new_game_json()) as GameState;
}

export async function createUI(): Promise<UiController> {
  const owner = new (await load()).OthelloUi();
  let freed = false;
  return {
    dispatch(action) {
      if (freed) throw new Error('Othello UI has been freed');
      return JSON.parse(owner.dispatch_json(JSON.stringify(action)));
    },
    free() {
      if (!freed) {
        freed = true;
        owner.free();
      }
    },
  };
}

export async function legalMoves(state: GameState): Promise<number[]> {
  return JSON.parse((await load()).legal_moves_json(JSON.stringify(state))) as number[];
}

export async function play(state: GameState, index: number): Promise<GameState> {
  // JS-to-Wasm u32 coercion must not turn negative/fractional/overflow input into a move.
  if (!Number.isInteger(index) || index < 0 || index > 0xffff_ffff) {
    throw new RangeError('move index must be an unsigned 32-bit integer');
  }
  return JSON.parse((await load()).apply_move_json(JSON.stringify(state), index)) as GameState;
}

export async function pass(state: GameState): Promise<GameState> {
  return JSON.parse((await load()).pass_turn_json(JSON.stringify(state))) as GameState;
}

export async function status(state: GameState): Promise<Status> {
  return JSON.parse((await load()).status_json(JSON.stringify(state))) as Status;
}

export async function chooseMove(state: GameState): Promise<number | null> {
  const choice = JSON.parse((await load()).choose_move_json(JSON.stringify(state))) as {
    move: number | null;
  };
  return choice.move;
}

// This awaits synchronous Wasm. Worker lifecycle cancellation belongs to the UI
// host; postMessage alone does not interrupt this search inside that Worker.
export async function search(state: GameState, options: SearchOptions = {}): Promise<SearchResult> {
  const encodedOptions = optionsJson(options);
  return JSON.parse(
    (await load()).search_json(JSON.stringify(state), encodedOptions),
  ) as SearchResult;
}

function optionsJson(options: SearchOptions): string {
  for (const [name, maximum] of [
    ['timeMs', Number.MAX_SAFE_INTEGER],
    ['ttMiB', 128],
    ['maxDepth', 64],
    ['exactEmpties', 64],
  ] as const) {
    const value = options[name];
    if (value !== undefined && (!Number.isSafeInteger(value) || value < 0 || value > maximum)) {
      throw new RangeError(`${name} must be an integer in 0..${maximum}`);
    }
  }
  return JSON.stringify(options);
}

/** Parse once into an explicit Wasm owner; never change baseline search globally.
 * Methods run synchronously in the owning Worker. Host owns artifact identity.
 */
export async function loadPattern(modelJson: string): Promise<PatternEvaluator> {
  const model = new (await load()).PatternModel(modelJson);
  let freed = false;
  const check = () => {
    if (freed) throw new Error('pattern model has been freed');
  };
  return {
    kind: 'patternV1',
    evaluate(state) {
      check();
      return JSON.parse(model.evaluate_json(JSON.stringify(state))) as EvaluationResult;
    },
    search(state, options = {}) {
      check();
      return JSON.parse(
        model.search_json(JSON.stringify(state), optionsJson(options)),
      ) as SearchResult;
    },
    free() {
      if (!freed) {
        freed = true;
        model.free();
      }
    },
  };
}
