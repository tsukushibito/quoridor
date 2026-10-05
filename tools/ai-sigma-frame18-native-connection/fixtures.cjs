'use strict';const fs=require('fs'),q=require('../ai-sigma-nnue-qf1-prototype/qf1.cjs');
fs.writeFileSync(process.argv[2],JSON.stringify(q.fixtureRows())+'\n');
console.log(JSON.stringify({NN:0,fixture_rows:q.fixtureRows().length,roots:q.fixtures().map(f=>f.id)}));
