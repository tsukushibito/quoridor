'use strict';
// Run after wasm-pack build --target nodejs --features nnue. This exercises the
// actual Wasm clock/model boundary, not a host Rust substitute.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const wasm = require(path.resolve(process.argv[2]));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'quoridor-wasm-nnue-'));
let engine;
try {
  const raw = Buffer.alloc(12193 * 4);
  for (let i = 0; i < 12193; i++) raw.writeFloatLE((((i * 73 + 19) % 101) - 50) / 1024, i * 4);
  const manifest = {
    feature: 'QF1-f32-STM-scaled-v1',
    weights: 'weights.f32',
    weights_SHA: crypto.createHash('sha256').update(raw).digest('hex'),
    weights_B: raw.length,
    little_endian_f32: 12193,
    mu_f32: [Math.fround(0.08), Math.fround(0.09)],
    sigma_f32: [Math.fround(0.05), Math.fround(0.06)],
    distance_fit: { a: 0.01, b: 7 },
  };
  const encoded = Buffer.from(JSON.stringify(manifest));
  fs.writeFileSync(path.join(temp, 'weights.f32'), raw);
  fs.writeFileSync(path.join(temp, 'manifest.json'), encoded);
  engine = new wasm.NnueEngine(encoded, raw);
  for (const prefix of [[], [81, 163], [13, 67, 22, 58, 31, 49, 40, 31]]) {
    const value = engine.evaluate(JSON.stringify(prefix));
    engine.set_simd(true);
    assert.equal(engine.evaluate(JSON.stringify(prefix)), value);
    engine.set_simd(false);
    assert(Number.isFinite(value) && Math.abs(value) <= 1);
    const r = JSON.parse(engine.search_json(JSON.stringify(prefix), 1, 2000, 0));
    assert.equal(r.completed_depth, 1);
    assert(Number.isInteger(r.action) && r.action >= 0 && r.action < 209);
  }
  const updates = [];
  const cancelled = JSON.parse(
    engine.search_with_updates_json('[]', 4, 20000, 1000, (json) => {
      updates.push(JSON.parse(json));
      return false;
    }),
  );
  assert.equal(updates.length, 1);
  assert.equal(cancelled.stop, 'Cancelled');
  assert.equal(cancelled.action, updates[0].action);
  const corrupted = Buffer.from(raw);
  corrupted[0] ^= 1;
  assert.throws(() => new wasm.NnueEngine(encoded, corrupted));
  assert.throws(() => engine.evaluate('[65535]'));
  console.log(
    JSON.stringify({
      schema: 'wasm-nnue-runtime-v1',
      fixtures: 3,
      scalar_simd_exact: true,
      completed_depth: cancelled.completed_depth,
      callback_cancel: true,
      hash_rejection: true,
    }),
  );
} finally {
  if (engine) engine.free();
  fs.rmSync(temp, { recursive: true, force: true });
}
