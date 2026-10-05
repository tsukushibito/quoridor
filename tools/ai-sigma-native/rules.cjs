'use strict';
const fs = require('node:fs'),
  vm = require('node:vm'),
  path = require('node:path');
// Each caller owns its State class/VM; no global frame, model or process state.
function createRules() {
  const ctx = vm.createContext({ console, Uint8Array, Float32Array, Uint32Array, Date, Math });
  for (const file of ['rules/game.js', 'rules/context.js'])
    vm.runInContext(fs.readFileSync(path.join(__dirname, file), 'utf8'), ctx, { filename: file });
  vm.runInContext(
    'this.rules = {State, fromPrefix, referenceState, requestState, rustAction, terminalResult}',
    ctx,
  );
  return { ctx, r: ctx.rules };
}
module.exports = { createRules };
