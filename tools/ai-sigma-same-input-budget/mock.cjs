'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const config = JSON.parse(fs.readFileSync(process.argv[2]));
const adapters = require('./adapters.cjs');
for (const name of ['main','worker','producer','checkpoint','cache']) new vm.Script(adapters.script(name));
assert.equal(config.requirements.length,18);
assert.equal(config.requirements.filter(r=>r.phase==='warm').length,2);
assert.equal(config.requirements.filter(r=>r.phase==='steady').length,16);
for (let i=0;i<4;i++) {
  const rows=config.requirements.filter(r=>r.phase==='steady'&&r.fixture_id===config.input_order[i]);
  assert.deepEqual(rows.map(r=>r.engine),i%2===0?['candidate','reference','reference','candidate']:['reference','candidate','candidate','reference']);
  for(const engine of ['candidate','reference'])assert.deepEqual(rows.filter(r=>r.engine===engine).map(r=>r.engine_repetition),[1,2]);
}
const source=adapters.script('main');
assert(source.includes('adopt_checkpoint:checkpoint?'));
assert(source.includes('await settlePlayerSearches();\n      await validateAfterProgression();'));
assert.equal(source.split('async function runSameInputBudget').length,2);
console.log(JSON.stringify({schedule18:true,steady16:true,warm2:true,root_sample8:true,syntax:true,adoption_CP_marker_only:true,full_diagnostic_after_zero:true,NN:0}));
