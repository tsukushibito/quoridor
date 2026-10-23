'use strict';
// Root-only selected exported weights; no old nominal/search fixture execution.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const spec = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
function bound(reference, maximum) {
  const before = fs.statSync(reference.path);
  assert(before.size <= maximum && before.size === reference.bytes);
  assert.equal((before.mode & 0o777).toString(8).padStart(4, '0'), reference.mode);
  const data = fs.readFileSync(reference.path);
  const after = fs.statSync(reference.path);
  assert.equal(data.length, reference.bytes);
  assert.equal(crypto.createHash('sha256').update(data).digest('hex'), reference.sha256);
  assert.equal(before.ino, after.ino);
  assert.equal(before.mtimeMs, after.mtimeMs);
  return data;
}
const inputRaw = bound(spec.native_input, 65536);
const input = JSON.parse(inputRaw);
const nativeRaw = bound(spec.native_result, 2 * 1024 ** 2);
const native = JSON.parse(nativeRaw);
const pythonRaw = bound(spec.python_result, 2 * 1024 ** 2);
const python = JSON.parse(pythonRaw);
assert.equal(native.status, 'COMPLETE');
assert.equal(python.status, 'COMPLETE');
assert.deepEqual(python.native_input, spec.native_input);
assert.deepEqual(python.native_result, spec.native_result);
assert.equal(native.input_sha256, crypto.createHash('sha256').update(inputRaw).digest('hex'));
assert.equal(native.rows.length, 32);
assert.equal(python.rows.length, 32);
for (const name of ['descriptor', 'weights', 'policy', 'policy_weights', 'input_classes']) {
  assert.deepEqual(native[name], input[name]);
}
const wasm = require(path.resolve(process.argv[2]));
const artifacts = [input.descriptor, input.weights, input.policy, input.policy_weights];
const bytes = artifacts.map((r) => bound(r, 65536));
let engine;
const result = {
  status: 'NOT_RUN',
  native_input: spec.native_input,
  native_result: spec.native_result,
  python_result: spec.python_result,
  head_attempted: 0,
  head_returned: 0,
  rows: [],
  H_rows: 0,
  Search_calls: 0,
  constructors: 0,
  constructor: 'NnuePolicyValue -> ResidualModel::load_bytes + PolicyHead::load_bytes',
  atol: 1e-5,
  rtol: 1e-4,
};
fs.writeFileSync(spec.output, JSON.stringify(result), { flag: 'wx' });
const save = () => fs.writeFileSync(spec.output, JSON.stringify(result));
const close = (actual, reference) => {
  assert(Number.isFinite(actual) && Number.isFinite(reference));
  assert(Math.abs(actual - reference) <= 1e-5 + 1e-4 * Math.abs(reference));
};
try {
  engine = new wasm.NnuePolicyValue(...bytes);
  result.constructors = 1;
  for (let i = 0; i < native.rows.length; i++) {
    const expected = native.rows[i];
    result.head_attempted++;
    save();
    const actual = JSON.parse(
      engine.evaluate_json(
        JSON.stringify({
          ruleset: 'standard_2p_threefold',
          prefix: expected.prefix,
        }),
      ),
    );
    result.head_returned++;
    result.rows.push(actual);
    save();
    assert.equal(Buffer.from(actual.shared_fingerprint).toString('hex'), input.shared_fingerprint);
    assert.equal(Buffer.from(actual.policy_fingerprint).toString('hex'), input.policy_fingerprint);
    assert.equal(actual.side, expected.side);
    assert.deepEqual(actual.legal, expected.legal);
    assert.equal(actual.logits.length, 209);
    assert(Math.abs(actual.value) <= 1);
    close(actual.value, expected.value);
    close(actual.value, python.rows[i].value);
    for (let a = 0; a < 209; a++) {
      close(actual.logits[a], expected.logits[a]);
      close(actual.logits[a], python.rows[i].logits[a]);
    }
  }
  for (const reference of artifacts) bound(reference, 65536);
  assert.deepEqual(bound(spec.native_result, 2 * 1024 ** 2), nativeRaw);
  assert.deepEqual(bound(spec.python_result, 2 * 1024 ** 2), pythonRaw);
  result.status = 'COMPLETE';
} catch (error) {
  result.status = 'FAILED';
  result.error = String(error);
  throw error;
} finally {
  if (engine) engine.free();
  save();
}
