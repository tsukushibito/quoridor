'use strict';
const fs = require('fs');
const crypto = require('crypto');
const base = require('../ai-sigma-diverse-prefix/adapters.cjs');
function replaceOnce(source, before, after) {
  if (source.split(before).length !== 2) throw Error('ADAPTER_COUNT ' + before);
  return source.replace(before, after);
}
function script(name) {
  let source = base.script(name);
  if (name === 'main') {
    source = replaceOnce(source, 'public_did_not_await_ACK:true,Node_clock_referee_calls:0', 'adopt_checkpoint:checkpoint?{sequence:checkpoint.sequence,action:checkpoint.action,visits:checkpoint.visits,value:checkpoint.value}:null,public_did_not_await_ACK:true,Node_clock_referee_calls:0');
    source += '\n' + fs.readFileSync(__dirname + '/budget-main.js', 'utf8');
  }
  return source;
}
function bindings() {
  return Object.fromEntries(Object.entries(base.bindings()).map(([name, value]) => [name, {...value, adapted_SHA256:crypto.createHash('sha256').update(script(name)).digest('hex')} ]));
}
module.exports = {script, bindings};
