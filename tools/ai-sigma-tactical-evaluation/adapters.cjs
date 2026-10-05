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
    source = replaceOnce(source, "simulations:spec.engine==='reference'?100000:4096", "simulations:spec.condition==='S'?1:spec.engine==='reference'?100000:4096");
    source = replaceOnce(source, 'public_did_not_await_ACK:true,Node_clock_referee_calls:0', 'adopt_checkpoint:checkpoint?{sequence:checkpoint.sequence,action:checkpoint.action,visits:checkpoint.visits,value:checkpoint.value}:null,public_did_not_await_ACK:true,Node_clock_referee_calls:0');
    source += '\n' + fs.readFileSync('../ai-sigma-tactical-oracle/checker.js'.replace('..', __dirname + '/..'), 'utf8');
    source += '\n' + fs.readFileSync(__dirname + '/tactical-main.js', 'utf8');
  }
  return source;
}
function bindings() {
  const values = Object.fromEntries(Object.entries(base.bindings()).map(([name, value]) => [name, {...value, adapted_SHA256:crypto.createHash('sha256').update(script(name)).digest('hex')} ]));
  values.oracle = {path:'tools/ai-sigma-tactical-oracle/checker.js', original_SHA256:crypto.createHash('sha256').update(fs.readFileSync(__dirname+'/../ai-sigma-tactical-oracle/checker.js')).digest('hex')};
  return values;
}
module.exports = {script, bindings};
