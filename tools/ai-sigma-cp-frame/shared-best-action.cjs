'use strict';

// One request owns one allocation. Every word uses Atomics, including f32 bits.
// A browser reader takes at most two samples and never waits for the writer.
const WORDS = 12;
const MAGIC = 0x43505341;
const STATE = { ACTIVE: 1, BUDGET_STOP: 2, CANCELLED: 3, FAULT: 4 };
const INDEX = {
  magic: 0, version: 1, generation: 2, state: 3, revision: 4,
  sequence: 5, action: 6, valueBits: 7, visits: 8, completed: 9,
};

function requireCondition(condition, reason) {
  if (!condition) throw new Error(reason);
}

function floatBits(value) {
  const data = new DataView(new ArrayBuffer(4));
  data.setFloat32(0, value, true);
  return data.getInt32(0, true);
}

function bitsFloat(bits) {
  const data = new DataView(new ArrayBuffer(4));
  data.setInt32(0, bits, true);
  return data.getFloat32(0, true);
}

function bind(buffer, context, expectedContext) {
  requireCondition(buffer instanceof SharedArrayBuffer && buffer.byteLength === WORDS * 4, 'SAB_SCHEMA');
  requireCondition(JSON.stringify(context) === JSON.stringify(expectedContext), 'SAB_CONTEXT');
  context = JSON.parse(JSON.stringify(context));
  requireCondition(Number.isInteger(context.generation) && context.generation > 0 && context.generation < 0x7fffffff, 'SAB_GENERATION');
  const words = new Int32Array(buffer);
  requireCondition(Atomics.load(words, INDEX.magic) === MAGIC && Atomics.load(words, INDEX.version) === 1, 'SAB_SCHEMA');
  requireCondition(Atomics.load(words, INDEX.generation) === context.generation, 'SAB_GENERATION');
  const legal = new Set(context.legalActions);
  requireCondition(legal.size === context.legalActions.length && [...legal].every(action => Number.isInteger(action) && action >= 0 && action < 209), 'SAB_LEGAL_SET');
  let cached = null;

  function usable() {
    const state = Atomics.load(words, INDEX.state);
    return Atomics.load(words, INDEX.generation) === context.generation && (state === STATE.ACTIVE || state === STATE.BUDGET_STOP);
  }

  function publish(cp) {
    requireCondition(cp.completed === true && Number.isInteger(cp.sequence) && cp.sequence > 0 && cp.sequence < 0x7fffffff, 'SAB_INCOMPLETE');
    requireCondition(legal.has(cp.action), 'SAB_ILLEGAL_ACTION');
    requireCondition(typeof cp.value === 'number' && Number.isFinite(cp.value) && Math.abs(cp.value) <= 1, 'SAB_VALUE');
    requireCondition(Number.isInteger(cp.visits) && cp.visits >= 0 && cp.visits < 0x7fffffff, 'SAB_VISITS');
    if (Atomics.load(words, INDEX.state) !== STATE.ACTIVE || Atomics.load(words, INDEX.generation) !== context.generation) return false;
    const revision = Atomics.load(words, INDEX.revision);
    requireCondition((revision & 1) === 0 && revision < 0x7ffffffc, 'SAB_WRITER_OR_OVERFLOW');
    requireCondition(cp.sequence > Atomics.load(words, INDEX.sequence), 'SAB_SEQUENCE');
    requireCondition(Atomics.compareExchange(words, INDEX.revision, revision, revision + 1) === revision, 'SAB_WRITER_COLLISION');
    Atomics.store(words, INDEX.sequence, cp.sequence);
    Atomics.store(words, INDEX.action, cp.action);
    Atomics.store(words, INDEX.valueBits, floatBits(cp.value));
    Atomics.store(words, INDEX.visits, cp.visits);
    Atomics.store(words, INDEX.completed, 1);
    Atomics.store(words, INDEX.revision, revision + 2);
    return Atomics.load(words, INDEX.state) === STATE.ACTIVE;
  }

  function readLatest() {
    if (!usable()) { cached = null; return null; }
    for (let attempt = 0; attempt < 2; attempt++) {
      const before = Atomics.load(words, INDEX.revision);
      if (before === 0 || (before & 1)) continue;
      const cp = {
        completed: Atomics.load(words, INDEX.completed) === 1,
        sequence: Atomics.load(words, INDEX.sequence),
        action: Atomics.load(words, INDEX.action),
        value: bitsFloat(Atomics.load(words, INDEX.valueBits)),
        visits: Atomics.load(words, INDEX.visits),
      };
      const after = Atomics.load(words, INDEX.revision);
      if (before !== after || (after & 1)) continue;
      requireCondition(cp.completed && legal.has(cp.action) && Number.isFinite(cp.value) && Math.abs(cp.value) <= 1 && cp.visits >= 0 && cp.sequence > 0, 'SAB_PAYLOAD');
      if (!usable()) { cached = null; return null; }
      cached = Object.freeze(cp);
      return cached;
    }
    return usable() ? cached : null;
  }

  function stop(reason) {
    const target = reason === 'budget' ? STATE.BUDGET_STOP : reason === 'cancel' ? STATE.CANCELLED : reason === 'fault' ? STATE.FAULT : null;
    requireCondition(target !== null, 'SAB_STOP_REASON');
    if (target === STATE.BUDGET_STOP) Atomics.compareExchange(words, INDEX.state, STATE.ACTIVE, target);
    else Atomics.store(words, INDEX.state, target);
    if (target !== STATE.BUDGET_STOP) cached = null;
  }

  function status() { return {state:Atomics.load(words,INDEX.state),generation:Atomics.load(words,INDEX.generation)}; }
  return { publish, readLatest, stop, status };
}

function create(context) {
  const buffer = new SharedArrayBuffer(WORDS * 4);
  const words = new Int32Array(buffer);
  Atomics.store(words, INDEX.magic, MAGIC);
  Atomics.store(words, INDEX.version, 1);
  Atomics.store(words, INDEX.generation, context.generation);
  Atomics.store(words, INDEX.state, STATE.ACTIVE);
  bind(buffer, context, context);
  return buffer;
}

const api = { create, bind, WORDS, INDEX, STATE };
if (typeof module !== 'undefined') module.exports = api;
globalThis.SharedBestAction = api;
