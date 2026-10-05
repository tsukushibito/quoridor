'use strict';
const path=require('path');const root=path.resolve(__dirname,'../..');const original=root+'/tools/ai-sigma-actual-boundary-repair/run-scope.cjs';const unchanged=require(original);
require.cache[require.resolve(original)].exports={...unchanged,BASE:root+'/.artifacts/ai-sigma/continuation-20261001/CRITIC-ACTUAL-DRIVER-MINIMAL/upstream'};
// Only output path changes. PLAN, ROOT, and original deadline stay unchanged.
