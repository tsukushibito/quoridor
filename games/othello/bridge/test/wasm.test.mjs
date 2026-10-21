// Root-only functional acceptance: requires the real wasm-pack web output.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { before, test } from 'node:test';
import {
  initSync,
  new_game_json,
  legal_moves_json,
  apply_move_json,
  pass_turn_json,
  status_json,
  choose_move_json,
} from '../wasm/othello.js';

before(() => {
  initSync({ module: readFileSync(new URL('../wasm/othello_bg.wasm', import.meta.url)) });
});

test('real Wasm exports the six fixed JSON operations', () => {
  const state = new_game_json();
  const parsed = JSON.parse(state);
  assert.equal(parsed.version, 1);
  assert.equal(parsed.toMove, 1);
  assert.equal(parsed.board.length, 64);
  assert.deepEqual(JSON.parse(legal_moves_json(state)), [19, 26, 37, 44]);
  assert.deepEqual(JSON.parse(choose_move_json(state)), { move: 19 });
  const next = JSON.parse(apply_move_json(state, 19));
  assert.equal(next.toMove, 2);
  assert.equal(next.board[19], 1);
  assert.equal(next.board[27], 1);
  assert.equal(JSON.parse(state).board[19], 0);
  assert.deepEqual(JSON.parse(status_json(state)), {
    black: 2,
    white: 2,
    legalMoves: [19, 26, 37, 44],
    mustPass: false,
    terminal: false,
    winner: null,
  });
  const board = Array(64).fill(0);
  board[0] = 1;
  board[1] = 2;
  const forced = JSON.stringify({ version: 1, board, toMove: 2 });
  assert.deepEqual(JSON.parse(choose_move_json(forced)), { move: null });
  assert.equal(JSON.parse(status_json(forced)).mustPass, true);
  assert.equal(JSON.parse(pass_turn_json(forced)).toMove, 1);
  board[1] = 1;
  const ended = JSON.stringify({ version: 1, board, toMove: 1 });
  assert.equal(JSON.parse(status_json(ended)).winner, 1);
  assert.deepEqual(JSON.parse(choose_move_json(ended)), { move: null });
  assert.throws(() => pass_turn_json(ended));
});

test('real Wasm reports invalid JSON, invalid moves and invalid pass as JS failures', () => {
  const state = new_game_json();
  for (const input of ['null', '{}', '{', JSON.stringify({ ...JSON.parse(state), version: 2 })]) {
    for (const call of [
      () => legal_moves_json(input),
      () => apply_move_json(input, 19),
      () => pass_turn_json(input),
      () => status_json(input),
      () => choose_move_json(input),
    ])
      assert.throws(call);
  }
  for (const index of [0, 27, 64, 275, 0xffff_ffff]) {
    assert.throws(() => apply_move_json(state, index));
  }
  assert.throws(() => pass_turn_json(state));
  assert.equal(state, new_game_json());
});
