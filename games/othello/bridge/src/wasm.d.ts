// Fallback declarations allow source-only checks before Root generates wasm-pack output.
declare module "*wasm/othello.js" {
  export default function init(options: {
    module_or_path: string;
  }): Promise<unknown>;
  export function new_game_json(): string;
  export function legal_moves_json(state: string): string;
  export function apply_move_json(state: string, index: number): string;
  export function pass_turn_json(state: string): string;
  export function status_json(state: string): string;
  export function choose_move_json(state: string): string;
  export function search_json(state: string, options: string): string;
  export class OthelloUi {
    constructor();
    dispatch_json(action: string): string;
    free(): void;
  }
}

declare module "*wasm/othello_bg.wasm?url" {
  const url: string;
  export default url;
}
