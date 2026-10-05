'use strict';
const assert = require('assert'),
  n = require('./nnue.cjs'),
  { q } = n;
function terminal(s, stats = {}) {
  stats.leaf_checks = (stats.leaf_checks ?? 0) + 1;
  const w = s.winner();
  if (w) {
    stats.leaf_winner = (stats.leaf_winner ?? 0) + 1;
    return { winner: w, value: w === s.getCurrentPlayer() ? 1 : -1 };
  }
  if (s.depth >= 200) {
    stats.leaf_draw200 = (stats.leaf_draw200 ?? 0) + 1;
    return { winner: 0, value: 0 };
  }
  assert.equal(typeof s._getLegalPawnActions, 'function', 'PAWN_EXISTENCE_UNAVAILABLE');
  const pawn = s._getLegalPawnActions();
  if (pawn.length) {
    stats.leaf_pawn_fast_nonterminal = (stats.leaf_pawn_fast_nonterminal ?? 0) + 1;
    return null;
  }
  stats.leaf_full_fallback = (stats.leaf_full_fallback ?? 0) + 1;
  return s.getLegalActions().length === 0 ? { winner: 0, value: 0 } : null;
}
function distanceKnownNonterminal(s, m) {
  const d = q.input(s).distance;
  return Math.max(
    -1,
    Math.min(
      1,
      Math.fround(
        Math.fround(m.distance_fit.a) +
          Math.fround(
            Math.fround(m.distance_fit.b) * Math.fround(Math.fround(d[1]) - Math.fround(d[0])),
          ),
      ),
    ),
  );
}
module.exports = { terminal, distanceKnownNonterminal };
