'use strict';
const fs = require('node:fs'),
  assert = require('node:assert');
const { input } = require('./features.cjs');
function load(file) {
  const b = fs.readFileSync(file);
  assert.equal(b.length, 48772);
  const w = new Float32Array(12193);
  for (let i = 0; i < w.length; i++) w[i] = b.readFloatLE(i * 4);
  assert(w.every(Number.isFinite));
  return {
    W: w.subarray(0, 9984),
    b: w.subarray(9984, 10016),
    H: w.subarray(10016, 12128),
    hb: w.subarray(12128, 12160),
    O: w.subarray(12160, 12192),
    ob: w[12192],
  };
}
const add = (a, b) => Math.fround(a + b),
  mul = (a, b) => Math.fround(a * b);
function full(s, w) {
  const q = input(s);
  const a = q.ids.map((ids) => {
    const v = new Float32Array(w.b);
    for (const k of ids) for (let j = 0; j < 32; j++) v[j] = add(v[j], w.W[j * 312 + k]);
    return v;
  });
  return { ...q, a };
}
function delta(parent, s, w) {
  const q = input(s);
  const updates = [];
  const a = parent.a.map((v, p) => {
    const out = new Float32Array(v),
      remove = parent.ids[p].filter((k) => !q.ids[p].includes(k)),
      insert = q.ids[p].filter((k) => !parent.ids[p].includes(k));
    for (const k of remove) for (let j = 0; j < 32; j++) out[j] = add(out[j], -w.W[j * 312 + k]);
    for (const k of insert) for (let j = 0; j < 32; j++) out[j] = add(out[j], w.W[j * 312 + k]);
    updates.push(remove.length + insert.length);
    return out;
  });
  return { ...q, a, updates };
}
function value(q, w) {
  const p = q.side - 1,
    other = 1 - p,
    x = Array.from(q.a[p], (v) => Math.max(0, v)).concat(
      Array.from(q.a[other], (v) => Math.max(0, v)),
      q.distance,
    );
  let out = w.ob;
  for (let j = 0; j < 32; j++) {
    let h = w.hb[j];
    for (let k = 0; k < 66; k++) h = add(h, mul(w.H[j * 66 + k], x[k]));
    out = add(out, mul(w.O[j], Math.max(0, h)));
  }
  return Math.fround(Math.tanh(out));
}
module.exports = { load, full, delta, value };
