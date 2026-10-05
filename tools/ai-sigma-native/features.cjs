'use strict';
const assert = require('node:assert');
const { r } = require('./rules.cjs').createRules();
const F = 'QF1-H32-f32-v1',
  cache = new Map();
let hit = 0,
  miss = 0;
function features(s, p) {
  assert.equal(s.boardsize, 9);
  const rot = p === 2,
    me = p === 1 ? s.player1pos : s.player2pos,
    op = p === 1 ? s.player2pos : s.player1pos;
  const square = (a) => {
    const i = a[1] * 9 + a[0];
    return rot ? 80 - i : i;
  };
  const out = [square(me), 81 + square(op)];
  for (const [o, base] of [
    [s.hwall_anchors, 162],
    [s.vwall_anchors, 226],
  ])
    for (const a of o) {
      const [x, y] = a.split(',').map(Number);
      assert(x >= 0 && x < 8 && y >= 0 && y < 8);
      const i = 8 * y + x;
      out.push(base + (rot ? 63 - i : i));
    }
  const rem = p === 1 ? [s.walls_p1, s.walls_p2] : [s.walls_p2, s.walls_p1];
  assert(rem.every((x) => Number.isInteger(x) && x >= 0 && x <= 10));
  out.push(290 + rem[0], 301 + rem[1]);
  out.sort((a, b) => a - b);
  assert.equal(new Set(out).size, out.length);
  assert(out.length <= 24 && out.every((i) => i >= 0 && i < 312));
  return out;
}
function maps(s) {
  const key =
    F +
    '|wallmap-graph1|9|goals8,0|' +
    [...s.hwall_anchors].sort().join(';') +
    '|' +
    [...s.vwall_anchors].sort().join(';');
  if (cache.has(key)) {
    hit++;
    return cache.get(key);
  }
  miss++;
  const result = [];
  for (const goal of [8, 0]) {
    const a = Array(81).fill(-1),
      q = [];
    for (let x = 0; x < 9; x++) {
      a[goal * 9 + x] = 0;
      q.push(goal * 9 + x);
    }
    for (let h = 0; h < q.length; h++) {
      const i = q[h],
        x = i % 9,
        y = Math.floor(i / 9);
      for (const [dx, dy] of [
        [0, 1],
        [0, -1],
        [1, 0],
        [-1, 0],
      ]) {
        const nx = x + dx,
          ny = y + dy,
          j = ny * 9 + nx;
        if (nx >= 0 && nx < 9 && ny >= 0 && ny < 9 && a[j] < 0 && !s._isEdgeBlocked(x, y, dx, dy)) {
          a[j] = a[i] + 1;
          q.push(j);
        }
      }
    }
    result.push(Object.freeze(a));
  }
  Object.freeze(result);
  if (cache.size >= 256) cache.clear();
  cache.set(key, result);
  return result;
}
function input(s) {
  const m = maps(s),
    d = [m[0][s.player1pos[1] * 9 + s.player1pos[0]], m[1][s.player2pos[1] * 9 + s.player2pos[0]]];
  assert(
    d.every((x) => x >= 0 && x <= 80),
    'UNREACHABLE_PAWN',
  );
  const side = s.getCurrentPlayer();
  return {
    ids: [features(s, 1), features(s, 2)],
    distance: side === 1 ? d.map((x) => x / 80) : d.reverse().map((x) => x / 80),
    side,
    maps: m,
  };
}
function clearCache() {
  cache.clear();
  hit = 0;
  miss = 0;
}
module.exports = {
  F,
  r,
  features,
  maps,
  input,
  clearCache,
  stats: () => ({ hits: hit, misses: miss, current: cache.size, max: 256 }),
};
