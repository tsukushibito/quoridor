'use strict';const fs=require('fs'),P=require('./proof-bundle.cjs'),J=require('./judge.cjs');
function fail(code){throw Object.assign(Error(code),{code})}
function check(c){const p=JSON.parse(fs.readFileSync(P.A+'/golden-preregister.json')),r=JSON.parse(fs.readFileSync(P.A+'/runtime-gate-control.json'));
 if(c.diagnostic_only!==true||c.actual_go!==false||c.mode!=='golden'||c.contract_version!==3||c.NN_allowed!==true||r.contract_version!==3||r.NN_allowed!==true||r.actual_go!==false||r.CPU!==2||r.threads!==1||r.RAM!==3221225472||r.guard!==2684354560||r.max_public!==5)fail('CURRENT_DIAGNOSTIC_NN_PERMISSION_REQUIRED');
 if(c.golden_preregister_sha256!==P.sha(P.A+'/golden-preregister.json')||p.subject_issue!=='quoridor-4lc.77'||p.contract_version!==3||p.max_public!==5||p.startup_root_NN!==6||p.requests.length!==5)fail('GOLDEN_PREREG_HASH');
 const fixtures=JSON.parse(fs.readFileSync(P.ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures,goal=fixtures.find(f=>f.id==='goal-win-legal-replay');
 const expected=[['initial-p1','candidate',[],false],['initial-p1','reference',[],false],['initial-p1','candidate',[],true],['goal-win-legal-replay','candidate',goal.legal_prefix,false],['goal-win-legal-replay','reference',goal.legal_prefix,false]];
 for(let i=0;i<5;i++){const q=p.requests[i],e=expected[i];if(q.id!==e[0]||q.engine!==e[1]||JSON.stringify(q.legal_prefix)!==JSON.stringify(e[2])||Boolean(q.cancel_after_cp)!==e[3])fail('GOLDEN_FIXED_REQUESTS');J.state(q.legal_prefix)}
 if(Date.now()>=Date.parse(c.processing_deadline_UTC))fail('PROCESSING_DEADLINE');return p;
}module.exports={check};
