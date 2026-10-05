'use strict';

// Valid-looking mock/tape policy is never admitted as a new training teacher.
function record(
  result,
  {
    lineage,
    split = 'diagnostic',
    side = 1,
    ply = 0,
    rootNN = null,
    source = 'NN0-diagnostic',
    mapping136 = null,
    legal_mask136 = null,
  } = {},
) {
  const checkpoint = result.cp;
  const edges = (checkpoint?.root_edges ?? []).map((edge) =>
    Array.isArray(edge) ? { action: edge[0], visits: edge[2], native209: true } : edge,
  );
  const edgeSum = edges.reduce((sum, edge) => sum + edge.visits, 0);
  const pi = Array(136).fill(0);
  const mapping = mapping136 ? new Map(mapping136) : null;
  let known = true;
  for (const edge of edges) {
    const action = mapping ? mapping.get(edge.action) : edge.native209 ? undefined : edge.action;
    if (!Number.isInteger(action) || action < 0 || action >= 136) {
      known = false;
      continue;
    }
    if (edgeSum > 0) pi[action] += edge.visits / edgeSum;
  }
  return {
    game_id: result.game_id,
    lineage,
    split,
    side,
    ply,
    rootN: checkpoint?.root_visits ?? 0,
    edgeSum,
    pi136: edgeSum && known ? pi : null,
    legal_mask136,
    rootNN,
    rootNN_view: 'side-to-move root NN; no teacher truth claim',
    rootmean: checkpoint?.root_mean ?? null,
    rootmean_view: 'side-to-move root search mean',
    leafNN: null,
    z_stm: null,
    z_p1: null,
    value_loss_mask: 0,
    policy_eligible: false,
    value_eligible: false,
    joint_eligible: false,
    reason: 'NN0_MOCK_OR_SAVED_TAPE_NOT_A_NEW_TEACHER',
    typed: result.typed,
    source,
    cost: result.counters,
  };
}

module.exports = { record };
