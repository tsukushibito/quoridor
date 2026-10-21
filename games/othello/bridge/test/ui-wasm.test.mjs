// Root-only changed-UI acceptance against freshly generated, real Othello Wasm.
// No skip or source-stub fallback. Does not invoke search or load a model.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { initSync, OthelloUi } from '../wasm/othello.js';

initSync({ module: readFileSync(new URL('../wasm/othello_bg.wasm', import.meta.url)) });
const send = (ui, action) => JSON.parse(ui.dispatch_json(JSON.stringify(action)));
const find = (out, kind) => out.effects.find((effect) => effect.kind === kind);
function start(ui, mode = 'local', humanSide = 1) {
  const ask = send(ui, { kind: 'new', mode, humanSide });
  assert.equal(find(ask, 'writeSave'), undefined);
  return send(ui, { kind: 'confirm', token: find(ask, 'confirm').token, accepted: true });
}
function reading(ui) {
  const ask = send(ui, { kind: 'resume' });
  const confirmed = send(ui, {
    kind: 'confirm',
    token: find(ask, 'confirm').token,
    accepted: true,
  });
  return find(confirmed, 'readSave').token;
}
const saved = (board, toMove = 1, mode = 'local', humanSide = 1) =>
  JSON.stringify({
    version: 1,
    game: 'othello',
    mode,
    humanSide,
    state: { version: 1, board, toMove },
  });
function withUi(body) {
  const ui = new OthelloUi();
  try {
    body(ui);
  } finally {
    ui.free();
  }
}

test('real Rust UI confirms new, projects accessible cells and applies only legal human moves', () =>
  withUi((ui) => {
    const initial = start(ui);
    assert.equal(initial.view.players, 'ローカル2人 · 黒：人間 ／ 白：人間');
    assert.equal(initial.view.cells.length, 64);
    assert.equal(initial.view.cells[19].enabled, true);
    assert.match(initial.view.cells[19].label, /D3.*合法手/);
    const original = JSON.parse(find(initial, 'writeSave').raw);
    const illegal = send(ui, { kind: 'play', index: 0 });
    assert.equal(find(illegal, 'writeSave'), undefined);
    const moved = send(ui, { kind: 'play', index: 19 }),
      written = find(moved, 'writeSave');
    assert.equal(written.key, 'othello.game.v1');
    assert.equal(original.state.board[19], 0);
    assert.equal(JSON.parse(written.raw).state.board[19], 1);
    assert.equal(moved.view.score, '黒 4 石 ／ 白 1 石');
  }));

test('real Rust UI retains corrupt or invalid original bytes through save and teardown', () => {
  for (const raw of [
    '{bad',
    saved(Array(64).fill(9)),
    saved(Array(64).fill(0), 0),
    JSON.stringify({ version: 2 }),
  ])
    withUi((ui) => {
      start(ui);
      const token = reading(ui);
      assert.equal(find(send(ui, { kind: 'save' }), 'writeSave'), undefined);
      const result = send(ui, { kind: 'loaded', token, raw, error: null });
      assert.ok(result.view.error);
      assert.equal(find(result, 'writeSave'), undefined);
      assert.equal(find(send(ui, { kind: 'play', index: 19 }), 'writeSave'), undefined);
      assert.equal(find(send(ui, { kind: 'dispose' }), 'writeSave'), undefined);
      assert.equal(
        find(
          send(ui, { kind: 'loaded', token, raw: saved(Array(64).fill(0)), error: null }),
          'writeSave',
        ),
        undefined,
      );
    });
});

test('real Rust UI refuses pending/failed resume writes and permits explicit confirmed replacement', () =>
  withUi((ui) => {
    start(ui);
    const token = reading(ui);
    assert.equal(find(send(ui, { kind: 'save' }), 'writeSave'), undefined);
    assert.equal(
      find(send(ui, { kind: 'loaded', token, raw: null, error: 'read denied' }), 'writeSave'),
      undefined,
    );
    assert.equal(find(send(ui, { kind: 'save' }), 'writeSave'), undefined);
    assert.ok(find(start(ui), 'writeSave'));
  }));

test('real Rust UI required pass and terminal with empty cells use actual core rules', () =>
  withUi((ui) => {
    const board = Array(64).fill(0);
    board[0] = 1;
    board[1] = 2;
    const loaded = send(ui, {
      kind: 'loaded',
      token: reading(ui),
      raw: saved(board, 2),
      error: null,
    });
    assert.equal(loaded.view.passVisible, true);
    assert.equal(loaded.view.passDisabled, false);
    assert.equal(find(send(ui, { kind: 'play', index: 2 }), 'writeSave'), undefined);
    assert.equal(send(ui, { kind: 'pass' }).view.passVisible, false);
    const terminal = send(ui, { kind: 'play', index: 2 });
    assert.equal(terminal.view.title, '終局：黒の勝ち');
    assert.equal(terminal.view.score, '黒 3 石 ／ 白 0 石');
    assert.equal(find(send(ui, { kind: 'pass' }), 'writeSave'), undefined);
  }));

test('real Rust UI rejects stale, mismatched and replayed Worker replies', () =>
  withUi((ui) => {
    const req = find(start(ui, 'ai', 2), 'think');
    const reply = { kind: 'aiReply', token: req.token, state: req.state, move: 19, error: null };
    assert.equal(
      find(
        send(ui, { ...reply, token: { ...req.token, request: req.token.request + 1 } }),
        'writeSave',
      ),
      undefined,
    );
    const wrong = structuredClone(req.state);
    wrong.toMove = 2;
    const mismatch = send(ui, { ...reply, state: wrong });
    assert.equal(find(mismatch, 'writeSave'), undefined);
    assert.equal(mismatch.view.retryAiVisible, true);
    const retry = find(send(ui, { kind: 'retryAi' }), 'think');
    assert.notDeepEqual(retry.token, req.token);
    const valid = { ...reply, token: retry.token, state: retry.state };
    assert.ok(find(send(ui, valid), 'writeSave'));
    assert.equal(find(send(ui, valid), 'writeSave'), undefined);
  }));

test('real Rust UI synchronously revokes AI ownership on new/resume/setup/cancel/dispose', () => {
  for (const kind of ['new', 'resume', 'setup', 'cancel', 'dispose'])
    withUi((ui) => {
      const req = find(start(ui, 'ai', 2), 'think');
      const action = ['new', 'setup'].includes(kind)
        ? { kind, mode: 'local', humanSide: 1 }
        : { kind };
      const revoked = send(ui, action);
      assert.ok(find(revoked, 'cancelWorker'));
      assert.ok(revoked.view.generation > req.token.generation);
      assert.equal(
        find(
          send(ui, { kind: 'aiReply', token: req.token, state: req.state, move: 19, error: null }),
          'writeSave',
        ),
        undefined,
      );
    });
});

test('real Rust UI reports write failure, restores it on cancelled confirmation, and acknowledges final save', () =>
  withUi((ui) => {
    const write = find(start(ui), 'writeSave');
    assert.match(
      send(ui, { kind: 'written', token: write.token, error: 'quota' }).view.exitWarning,
      /quota/,
    );
    const ask = send(ui, { kind: 'new', mode: 'ai', humanSide: 2 });
    const cancelled = send(ui, {
      kind: 'confirm',
      token: find(ask, 'confirm').token,
      accepted: false,
    });
    assert.match(cancelled.view.exitWarning, /quota/);
    const final = find(send(ui, { kind: 'dispose' }), 'writeSave');
    assert.ok(final);
    assert.equal(
      send(ui, { kind: 'written', token: final.token, error: null }).view.exitWarning,
      null,
    );
    assert.equal(
      find(send(ui, { kind: 'new', mode: 'local', humanSide: 1 }), 'confirm'),
      undefined,
    );
  }));
