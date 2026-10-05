'use strict';
// Compatibility for frozen recipes and their mock export. New callers supply an explicit run ID.
const { GamePool: SharedGamePool } = require('../ai-sigma-common/generation/game-pool.cjs');
class GamePool extends SharedGamePool {
  constructor(worker, backend, broker, { run = 'native185-mock', maxHandles = 8 } = {}) {
    if (![4, 8].includes(maxHandles)) throw Error('HANDLE_CAP');
    super(worker, backend, broker, { run, maxHandles });
  }
}
module.exports = { GamePool, ...require('./mock-registry.cjs') };
