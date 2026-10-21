// Root-only functional acceptance: requires the real wasm-pack web output.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { before, test } from 'node:test';
import { spawnSync } from 'node:child_process';
import {
  initSync,
  new_game_json,
  legal_moves_json,
  apply_move_json,
  pass_turn_json,
  status_json,
  choose_move_json,
  search_json,
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

test('real Wasm search uses a browser clock and retains legal zero-budget fallback', () => {
  const initial = new_game_json();
  const zero = JSON.parse(search_json(initial, JSON.stringify({ timeMs: 0, ttMiB: 0 })));
  assert.equal(zero.move, 19);
  assert.equal(zero.completedDepth, 0);
  assert.equal(zero.nodes, 0);
  assert.equal(zero.scoreKind, 'heuristic');
  assert.equal(zero.proven, false);
  assert.equal(zero.timedOut, true);
  assert.equal(zero.cancelled, false);
  assert.ok(zero.elapsedMs >= 0 && Number.isFinite(zero.elapsedMs));
  const searched = JSON.parse(
    search_json(initial, JSON.stringify({ timeMs: 1000, ttMiB: 0, maxDepth: 2 })),
  );
  assert.ok([19, 26, 37, 44].includes(searched.move));
  assert.equal(searched.completedDepth, 2);
  assert.equal(searched.proven, false);
  assert.equal(searched.timedOut, false);
  assert.ok(searched.nodes > 0);
  assert.throws(() => search_json(initial, '{'));
  assert.throws(() => search_json(initial, JSON.stringify({ ttMiB: 129 })));
  assert.throws(() => search_json('{}', '{}'));
});

test('real Wasm exact early end and forced pass preserve actual disc scoring', () => {
  const board = Array(64).fill(0);
  board[0] = 1;
  board[1] = 2;
  const forced = JSON.stringify({ version: 1, board, toMove: 2 });
  const options = JSON.stringify({ timeMs: 1000, ttMiB: 0, exactEmpties: 64 });
  const result = JSON.parse(search_json(forced, options));
  assert.equal(result.move, null);
  assert.equal(result.proven, true);
  assert.equal(result.scoreKind, 'discDifference');
  assert.equal(result.score, -3);
  board[1] = 1;
  const terminal = JSON.parse(
    search_json(JSON.stringify({ version: 1, board, toMove: 1 }), '{"timeMs":0}'),
  );
  assert.equal(terminal.score, 2);
  assert.equal(terminal.proven, true);
  assert.equal(terminal.move, null);
  assert.equal(terminal.completedDepth, 0);
});

test('real native/Wasm search JSON parity', { skip: !process.env.OTHELLO_NATIVE_ENGINE }, () => {
  const initial = JSON.parse(new_game_json());
  const forced = { version: 1, board: Array(64).fill(0), toMove: 2 };
  forced.board[0] = 1;
  forced.board[1] = 2;
  const terminal = { ...forced, board: [...forced.board], toMove: 1 };
  terminal.board[1] = 1;
  const cases = [
    [initial, { timeMs: 1000, ttMiB: 0, maxDepth: 3 }],
    [
      JSON.parse(apply_move_json(JSON.stringify(initial), 19)),
      { timeMs: 1000, ttMiB: 0, maxDepth: 3 },
    ],
    [initial, { timeMs: 0, ttMiB: 0 }],
    [forced, { timeMs: 1000, ttMiB: 0, exactEmpties: 64 }],
    [terminal, { timeMs: 0, ttMiB: 0 }],
  ];
  const input = cases.map(([state, options]) =>
    JSON.stringify({ op: 'search', state, ...options }),
  );
  const native = spawnSync(process.env.OTHELLO_NATIVE_ENGINE, [], {
    input: input.join('\n') + '\n',
    encoding: 'utf8',
    timeout: 10000,
    maxBuffer: 1024 * 1024,
  });
  assert.ifError(native.error);
  assert.equal(native.status, 0, native.stderr);
  const responses = native.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(responses.length, cases.length);
  for (const [index, [state, options]] of cases.entries()) {
    const wasm = JSON.parse(search_json(JSON.stringify(state), JSON.stringify(options)));
    assert.equal(responses[index].ok, true);
    for (const key of [
      'move',
      'score',
      'scoreKind',
      'completedDepth',
      'nodes',
      'timedOut',
      'cancelled',
      'proven',
    ]) {
      assert.equal(wasm[key], responses[index][key], `case ${index} field ${key}`);
    }
  }
});
