'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { q } = require('../search.cjs');
function positive(value, name) {
  assert(Number.isSafeInteger(value) && value > 0 && value <= 0x7fffffff, `CONFIG_${name}`);
}
function validateConfig(c) {
  assert.equal(c.schema, 'native-arena-run-v1');
  for (const key of ['run', 'issue', 'owner', 'goal_issue'])
    assert(
      typeof c[key] === 'string' && c[key].length > 0 && c[key].length <= 256,
      `CONFIG_${key}`,
    );
  for (const key of [
    'weight_manifest',
    'openings',
    'hands',
    'counter_file',
    'output',
    'output_root',
    'beads_wrapper',
    'pause_path',
  ])
    assert(typeof c[key] === 'string' && path.isAbsolute(c[key]), `CONFIG_${key}_ABSOLUTE`);
  for (const key of [
    'NNcap',
    'node_cap',
    'max_depth',
    'budget_ms',
    'init_timeout_ms',
    'cleanup_ms',
  ])
    positive(c[key], key);
  assert(
    Number.isFinite(c.margin_ms) && c.margin_ms >= 0 && c.margin_ms < c.budget_ms,
    'CONFIG_margin_ms',
  );
  assert(
    Array.isArray(c.slots) &&
      c.slots.length &&
      c.slots.every((x) => typeof x === 'string' || Number.isSafeInteger(x)) &&
      new Set(c.slots).size === c.slots.length,
    'CONFIG_slots',
  );
  assert(Number.isFinite(Date.parse(c.end_utc)), 'CONFIG_end_utc');
  assert(
    Number.isFinite(Date.parse(c.heavy_start_cutoff_utc)) &&
      Date.parse(c.heavy_start_cutoff_utc) <= Date.parse(c.end_utc),
    'CONFIG_heavy_start_cutoff_utc',
  );
  assert(['rootbest-first', 'reference-order'].includes(c.ordering), 'CONFIG_ordering');
  const outputs = ['hands', 'counter_file', 'output'].map((k) => path.resolve(c[k]));
  assert.equal(new Set(outputs).size, outputs.length, 'OUTPUT_COLLISION');
  for (const output of outputs)
    assert(path.dirname(output) === path.resolve(c.output_root), 'OUTPUT_ROOT');
  const root = path.resolve(c.output_root);
  for (const key of ['weight_manifest', 'openings', 'beads_wrapper', 'pause_path'])
    assert(
      ![root, ...outputs].includes(path.resolve(c[key])) &&
        !path.resolve(c[key]).startsWith(root + path.sep),
      'INPUT_OUTPUT_COLLISION',
    );
  const resources = c.resources;
  assert(
    resources &&
      Array.isArray(resources.affinity) &&
      resources.affinity.length &&
      resources.affinity.every((x) => Number.isSafeInteger(x) && x >= 0),
    'CONFIG_affinity',
  );
  assert.equal(
    new Set(resources.affinity).size,
    resources.affinity.length,
    'CONFIG_affinity_duplicate',
  );
  for (const key of [
    'logical_cpu_limit',
    'ram_guard_bytes',
    'output_cap_bytes',
    'max_snapshot_bytes',
  ])
    positive(resources[key], key);
  assert(resources.affinity.length <= resources.logical_cpu_limit, 'CONFIG_CPU_BUDGET');
  assert(
    resources.max_snapshot_bytes * 2 + 16384 <= resources.output_cap_bytes,
    'CONFIG_OUTPUT_FORECAST',
  );
  assert(c.transport && typeof c.transport === 'object', 'CONFIG_transport');
  for (const key of [
    'maxQueueMessages',
    'maxQueueBytes',
    'maxReplyBytes',
    'maxRequestBytes',
    'maxStderrBytes',
    'stopTimeoutMs',
    'closeGraceMs',
    'killGraceMs',
  ])
    positive(c.transport[key], key);
  assert(
    c.cleanup_ms >= c.transport.closeGraceMs + 2 * c.transport.killGraceMs + 1000,
    'CONFIG_CLEANUP_BUDGET',
  );
  return c;
}
function validatePlan(manifest, c) {
  assert(
    manifest && Array.isArray(manifest.slots) && Array.isArray(manifest.openings),
    'PLAN_SCHEMA',
  );
  const openings = new Map();
  for (const opening of manifest.openings) {
    assert(
      opening &&
        (typeof opening.id === 'string' || Number.isSafeInteger(opening.id)) &&
        !openings.has(opening.id),
      'PLAN_OPENING_ID',
    );
    assert(Array.isArray(opening.prefix), 'PLAN_PREFIX');
    q.r.fromPrefix(opening.prefix); // legal history, not just JSON shape
    openings.set(opening.id, opening);
  }
  const slots = new Map();
  for (const slot of manifest.slots) {
    assert(
      slot &&
        (typeof slot.slot === 'string' || Number.isSafeInteger(slot.slot)) &&
        !slots.has(slot.slot),
      'PLAN_SLOT_ID',
    );
    assert(openings.has(slot.opening), 'PLAN_OPENING_MISSING');
    assert(
      [1, 2].includes(slot.NNUE_side) && ['clip', 'tanh'].includes(slot.distance_mode),
      'PLAN_ENGINE_CONDITION',
    );
    slots.set(slot.slot, { ...slot, status: 'NOT_STARTED' });
  }
  assert(
    c.slots.every((id) => slots.has(id)),
    'PLAN_SLOT_MISSING',
  );
  return { ledger: c.slots.map((id) => slots.get(id)), openings };
}
function checkStart(c, time = Date.now()) {
  assert(time < Date.parse(c.heavy_start_cutoff_utc), 'NEWHEAVY_CUTOFF');
  assert(
    time + c.init_timeout_ms + c.budget_ms + c.transport.stopTimeoutMs + c.cleanup_ms <
      Date.parse(c.end_utc),
    'RUN_DOES_NOT_FIT_DEADLINE',
  );
}
function readJSON(file, cap = 1024 * 1024) {
  assert(fs.statSync(file).isFile() && fs.statSync(file).size <= cap, 'INPUT_CAP');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
module.exports = { validateConfig, validatePlan, checkStart, readJSON };
