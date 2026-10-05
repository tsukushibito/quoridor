'use strict';
const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path');
const { createReference } = require('../reference.cjs');
const { createRules } = require('../rules.cjs');
const q = require('../features.cjs'),
  w = require('../weights.cjs'),
  n = require('../nnue.cjs'),
  search = require('../search.cjs');
// Baseline 18119197; frozen modules are used as rule/feature oracles only, never inference.
const old = require('../../ai-sigma-nnue-qf1-prototype/qf1.cjs');
const oldSearch = require('../../ai-sigma-frame20-distance-arena/engine.cjs');
const json = (x) => JSON.parse(JSON.stringify(x));
const prefixes = [
  [],
  [{ type: 'pawn', direction: [0, 1] }],
  [{ type: 'wall', orientation: 'h', x: 2, y: 3 }],
  [
    { type: 'pawn', direction: [0, 1] },
    { type: 'wall', orientation: 'v', x: 4, y: 3 },
  ],
];
test('isolated rule factory matches legal order, f32 input, history and successors', () => {
  for (const prefix of prefixes) {
    const s = q.r.fromPrefix(prefix),
      o = old.r.fromPrefix(prefix);
    assert.deepEqual(json(s.getLegalActions()), json(o.getLegalActions()));
    assert.deepEqual(Array.from(s.toNNInput()), Array.from(o.toNNInput()));
    assert.equal(n.history(s), n.history(o));
    assert.equal(s._positionKey(), o._positionKey());
    const before = n.history(s);
    for (const action of s.getLegalActions().slice(0, 8)) {
      const c = s.next(action),
        z = o.next(action);
      assert.equal(n.history(c), n.history(z));
      assert.equal(q.r.rustAction(s, action), old.r.rustAction(o, action));
    }
    assert.equal(n.history(s), before);
  }
  assert.notEqual(createRules().r.State, createRules().r.State);
  assert.throws(() => q.r.fromPrefix([{ type: 'pawn', direction: [5, 5] }]), /invalid-prefix/);
});
test('QF1 STM ids, normalized distances and cache lifecycle preserve baseline', () => {
  q.clearCache();
  for (const prefix of prefixes) {
    const s = q.r.fromPrefix(prefix),
      o = old.r.fromPrefix(prefix);
    const a = q.input(s),
      b = old.input(o);
    assert.deepEqual(json(a), json(b));
    assert.deepEqual(q.features(s, 2), old.features(o, 2));
  }
  q.input(q.r.fromPrefix([]));
  assert(q.stats().hits > 0);
  q.clearCache();
  assert.equal(q.stats().current, 0);
});
test('weight codec is finite strict f32 and feature full/delta preserves parent', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'qf1-contract-'));
  try {
    const file = path.join(dir, 'synthetic.bin'),
      bytes = Buffer.alloc(48772);
    for (let i = 0; i < 12193; i++) bytes.writeFloatLE((i % 3) - 1, i * 4);
    fs.writeFileSync(file, bytes);
    const weights = w.load(file),
      s = q.r.fromPrefix([]),
      a = w.full(s, weights),
      saved = a.a.map((x) => Array.from(x));
    for (const action of s.getLegalActions().slice(0, 8)) {
      const c = s.next(action),
        d = w.delta(a, c, weights),
        f = w.full(c, weights);
      assert.deepEqual(
        d.a.map((x) => Array.from(x)),
        f.a.map((x) => Array.from(x)),
      );
      assert.deepEqual(
        a.a.map((x) => Array.from(x)),
        saved,
      );
    }
    bytes.writeFloatLE(NaN, 0);
    fs.writeFileSync(file, bytes);
    assert.throws(() => w.load(file));
    fs.writeFileSync(file, Buffer.alloc(4));
    assert.throws(() => w.load(file));
  } finally {
    fs.rmSync(dir, { recursive: true });
  }
});
test('history/terminal priority and explicit search configuration preserve completed-depth behavior', () => {
  const m = { distance_fit: { a: 0, b: 1 } },
    config = {
      leafPackage: true,
      distanceMode: 'clip',
      nodeCap: 256,
      maxDepth: 1,
      deadlineMs: Infinity,
      ordering: 'rootbest-first',
    };
  for (const prefix of prefixes.slice(0, 2)) {
    const s = q.r.fromPrefix(prefix);
    const a = search.search(s, 'distance', null, m, config),
      b = oldSearch.search(old.r.fromPrefix(prefix), 'distance', null, m, config);
    assert.equal(a.Action, b.Action);
    assert.equal(a.value, b.value);
    assert.equal(a.stats.processed, b.stats.processed);
    assert(a.parent_copy_key_history_restored);
  }
  assert.throws(
    () => search.search(q.r.fromPrefix([]), 'distance', null, m, { leafPackage: true }),
    /RUN_CONFIG/,
  );
  const stopped = search.search(q.r.fromPrefix([]), 'distance', null, m, {
    ...config,
    nodeCap: 1,
    maxDepth: 2,
  });
  assert.equal(stopped.status, 'NO_COMPLETED_DEPTH');
  assert.equal(stopped.typed_stop, 'NODE_CAP');
  assert.equal(stopped.depths[0].adopted, false);
  const cancel = search.search(q.r.fromPrefix([]), 'distance', null, m, {
    ...config,
    stop: () => true,
  });
  assert.equal(cancel.typed_stop, 'CANCELLED');
  const draw = q.r.fromPrefix([]);
  draw.depth = 200;
  assert.deepEqual(json(q.r.terminalResult(draw)), { winner: 0, value: 0 });
});
test('MCTS reference factory exports current closure without starting a process/model', () => {
  const { r } = createReference();
  assert.equal(typeof r.runMCTS, 'function');
  assert.deepEqual(
    json(r.fromPrefix([]).getLegalActions()),
    json(q.r.fromPrefix([]).getLegalActions()),
  );
});
test('current controller owns and closes its mock reference child without neural work', async () => {
  const { Engine } = require('../controller.cjs');
  assert.throws(() => new Engine('reference'), /pipeTimeoutMs/);
  const e = new Engine('reference', null, { pipeTimeoutMs: 1000 });
  const info = await e.init(true);
  assert.equal(info.mock, true);
  assert.equal(info.identities.length, 1);
  const closed = await e.close();
  assert.equal(closed.exit.code, 0);
  assert.equal(closed.receipt.NN_total, 0);
  assert(e.closed);
});
test('scaled manifest binds exact weight hash/shape and finite positive STM statistics', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'qf1-manifest-'));
  try {
    const bytes = Buffer.alloc(48772),
      weights = path.join(directory, 'weights.bin'),
      file = path.join(directory, 'manifest.json');
    fs.writeFileSync(weights, bytes);
    const m = {
      feature: 'QF1-f32-STM-scaled-v1',
      weights: 'weights.bin',
      weights_SHA: require('node:crypto').createHash('sha256').update(bytes).digest('hex'),
      weights_B: 48772,
      little_endian_f32: 12193,
      mu_f32: [0, 0],
      sigma_f32: [1, 1],
      distance_fit: { a: 0, b: 1 },
    };
    fs.writeFileSync(file, JSON.stringify(m));
    assert.equal(n.load(file).m.weights, weights);
    for (const patch of [
      { weights_SHA: '0'.repeat(64) },
      { sigma_f32: [0, 1] },
      { mu_f32: [0] },
      { distance_fit: { a: null, b: 1 } },
      { feature: 'wrong' },
    ]) {
      fs.writeFileSync(file, JSON.stringify({ ...m, ...patch }));
      assert.throws(() => n.load(file));
    }
  } finally {
    fs.rmSync(directory, { recursive: true });
  }
});

test('weight path physical size refuses before reading unexpected large input', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'manifest-size-'));
  try {
    const weights = path.join(dir, 'large'),
      file = path.join(dir, 'manifest.json');
    const fd = fs.openSync(weights, 'w');
    fs.ftruncateSync(fd, 4 * 1024 * 1024);
    fs.closeSync(fd);
    const m = {
      feature: 'QF1-f32-STM-scaled-v1',
      weights,
      weights_SHA: '0'.repeat(64),
      weights_B: 48772,
      little_endian_f32: 12193,
      mu_f32: [0, 0],
      sigma_f32: [1, 1],
      distance_fit: { a: 0, b: 1 },
    };
    fs.writeFileSync(file, JSON.stringify(m));
    assert.throws(() => n.load(file), /WEIGHTS_PHYSICAL_SIZE/);
  } finally {
    fs.rmSync(dir, { recursive: true });
  }
});
