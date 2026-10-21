// No Wasm import or initialization runs until an exported operation is requested.
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
