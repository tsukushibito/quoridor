'use strict';

// An NN response belongs to one run, worker, game, tree generation, handle and token.
const fields = Object.freeze([
  'run_id',
  'worker_id',
  'game_id',
  'generation',
  'handle',
  'token',
  'request_id',
]);

function validate(identity) {
  if (!identity || fields.some((field) => identity[field] === undefined)) {
    throw Error('IDENTITY_SCHEMA');
  }
  for (const field of ['run_id', 'worker_id', 'game_id', 'request_id']) {
    const value = identity[field];
    if (typeof value !== 'string' || !value || value.length > 128) {
      throw Error('IDENTITY_SCHEMA');
    }
  }
  for (const field of ['generation', 'handle', 'token']) {
    if (!Number.isSafeInteger(identity[field]) || identity[field] < 0) {
      throw Error('IDENTITY_SCHEMA');
    }
  }
  return Object.freeze(Object.fromEntries(fields.map((field) => [field, identity[field]])));
}

function key(identity) {
  return JSON.stringify(fields.map((field) => identity[field]));
}

function owner(identity) {
  return JSON.stringify([identity.run_id, identity.worker_id, identity.game_id]);
}

function features(bits) {
  if (
    !Array.isArray(bits) ||
    bits.length !== 648 ||
    bits.some(
      (value) =>
        !Number.isInteger(value) ||
        value < 0 ||
        value > 0xffffffff ||
        (value & 0x7f800000) === 0x7f800000,
    )
  ) {
    throw Error('FEATURE_SCHEMA');
  }
  return bits;
}

module.exports = { fields, validate, key, owner, features };
