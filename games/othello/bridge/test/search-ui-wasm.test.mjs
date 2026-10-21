// Root-only changed-boundary tests with actual regenerated Othello Wasm.
// First case performs one real baseline search; later cases use stated transport
// fixtures to check the Rust UI fence, not search strength or search timing.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { initSync, OthelloUi, search_json } from '../wasm/othello.js';
initSync({ module: readFileSync(new URL('../wasm/othello_bg.wasm', import.meta.url)) });
const send = (ui, value) => JSON.parse(ui.dispatch_json(JSON.stringify(value)));
const effect = (out, kind) => out.effects.find((e) => e.kind === kind);
function start(ui, strategy = 'searchV1') {
  const ask = send(ui, { kind: 'new', mode: 'ai', humanSide: 2, strategy });
  return send(ui, { kind: 'confirm', token: effect(ask, 'confirm').token, accepted: true });
}
const fixture = {
  move: 19,
  score: 0,
  scoreKind: 'heuristic',
  completedDepth: 1,
  nodes: 1,
  elapsedMs: 1000,
  timedOut: true,
  cancelled: false,
  proven: false,
};
const reply = (req, searchResult = fixture) => ({
  kind: 'aiReply',
  token: req.token,
  state: req.state,
  strategy: req.strategy,
  move: searchResult.move,
  searchResult,
  error: null,
});

test('actual one-second baseline Wasm result commits through the Rust searchV1 UI boundary', (t) => {
  const ui = new OthelloUi();
  try {
    const req = effect(start(ui), 'think');
    assert.equal(req.strategy, 'searchV1');
    const options = { timeMs: 1000, ttMiB: 32, maxDepth: 64, exactEmpties: 12 };
    const actual = JSON.parse(search_json(JSON.stringify(req.state), JSON.stringify(options)));
    t.diagnostic(JSON.stringify({ strategy: req.strategy, options, result: actual }));
    assert.equal(actual.cancelled, false);
    const moved = send(ui, reply(req, actual));
    assert.equal(moved.view.error, '');
    const saved = JSON.parse(effect(moved, 'writeSave').raw);
    assert.equal(saved.strategy, 'searchV1');
    assert.equal(saved.state.board.filter(Boolean).length, 5);
    assert.equal(saved.state.toMove, 2);
    assert.equal(saved.state.board[actual.move], 1);
  } finally {
    ui.free();
  }
});

test('actual Rust/Wasm UI defaults legacy saves to simple and retains invalid-strategy save bytes', () => {
  const ui = new OthelloUi();
  try {
    const initial = start(ui, 'simple'),
      legacy = JSON.parse(effect(initial, 'writeSave').raw);
    delete legacy.strategy;
    function load(raw) {
      const ask = send(ui, { kind: 'resume' });
      const read = send(ui, {
        kind: 'confirm',
        token: effect(ask, 'confirm').token,
        accepted: true,
      });
      return send(ui, { kind: 'loaded', token: effect(read, 'readSave').token, raw, error: null });
    }
    const loaded = load(JSON.stringify(legacy));
    assert.equal(effect(loaded, 'think').strategy, 'simple');
    assert.equal(JSON.parse(effect(loaded, 'writeSave').raw).strategy, 'simple');
    legacy.strategy = 'learned';
    const bad = load(JSON.stringify(legacy));
    assert.ok(bad.view.error);
    assert.equal(effect(bad, 'writeSave'), undefined);
    assert.equal(effect(send(ui, { kind: 'save' }), 'writeSave'), undefined);
    assert.equal(effect(send(ui, { kind: 'dispose' }), 'writeSave'), undefined);
  } finally {
    ui.free();
  }
});

test('actual Rust/Wasm UI rejects cancelled/mismatched/illegal search fixtures and stale old strategy', () => {
  for (const kind of ['cancelled', 'strategy', 'illegal', 'proof', 'stale']) {
    const ui = new OthelloUi();
    try {
      const req = effect(start(ui), 'think'),
        input = reply(req);
      if (kind === 'cancelled') input.searchResult = { ...fixture, cancelled: true };
      if (kind === 'strategy') input.strategy = 'simple';
      if (kind === 'illegal') {
        input.move = 0;
        input.searchResult = { ...fixture, move: 0 };
      }
      if (kind === 'proof') input.searchResult = { ...fixture, proven: true };
      if (kind === 'stale')
        send(ui, { kind: 'setup', mode: 'ai', humanSide: 2, strategy: 'simple' });
      const rejected = send(ui, input);
      assert.equal(effect(rejected, 'writeSave'), undefined);
      if (kind !== 'stale') assert.equal(rejected.view.retryAiVisible, true);
      assert.equal(rejected.view.cells.filter((c) => c.stone).length, 4);
    } finally {
      ui.free();
    }
  }
});
