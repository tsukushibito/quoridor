'use strict';
const fs=require('fs'),path=require('path'),CP=require('child_process'),assert=require('assert/strict'),P=require('./proof-bundle.cjs'),{make}=require('./make-diagnostic.cjs');
const prefix=process.env.SIGMA77_RUN_ID;assert(/^[a-z0-9_-]+$/.test(prefix));const rows=[];
function cli(token,flag='--diagnostic-actual'){
 const command=[path.join(__dirname,'match-entry.cjs'),flag,...(token?[token]:[])];
 const c=CP.spawnSync(process.execPath,['--max-old-space-size=192','--max-semi-space-size=4','--no-node-snapshot',...command],{env:{...process.env,SIGMA77_FREEZE_TOKEN:'DIAGNOSTIC77_ONLY_NOT_ACTUAL'},encoding:'utf8',timeout:18000});
 rows.push({command,exit:c.status,signal:c.signal,stdout:c.stdout,stderr:c.stderr});return c;
}
const read=(id,n)=>JSON.parse(fs.readFileSync(P.A+'/diagnostic-actual/'+id+'/'+n+'.json'));
function failure(name,opt,code,flag='--diagnostic-actual'){
 const id=prefix+'-'+name,token=make(id,opt),c=cli(token,flag);assert.equal(c.status,1,c.stderr);assert(c.stderr.includes(code),c.stderr);
 const p=P.A+'/diagnostic-actual/'+id+'/driver-monitor-stop.json';if(fs.existsSync(p)){const z=read(id,'driver-monitor-stop');assert.equal(z.owned_read_children_zero,true);assert.equal(z.factoryCalls,0);}
 return id;
}
async function main(){
 const id=prefix+'-positive',token=make(id),c=cli(token);assert.equal(c.status,0,c.stderr);
 const d=read(id,'driver-result'),r=d.result;assert.equal(r.purpose,'actual');assert.equal(r.diagnostic,true);assert.equal(r.actual_go,false);assert.equal(r.dry,true);
 assert.equal(r.audit.backend_dispatches,2);assert.equal(r.audit.mock_dispatches,2);assert.equal(r.audit.real_engine_dispatches,0);assert.equal(r.audit.public_responses,2);assert.equal(r.audit.accepted_responses,1);assert.equal(r.audit.completed_games,0);assert.equal(r.actual_games,0);assert.equal(r.holdout_sends,0);assert.equal(r.audit.attempts,0);assert.equal(r.NN,0);assert.equal(r.browser,0);assert.equal(r.cleanupFailed,false);assert.equal(r.unrecovered_preparations,0);
 assert(read(id,'monitor-ready').ready);assert(read(id,'driver-monitor-stop').owned_read_children_zero);
 const mon=read(id,'pause-monitor-stop');assert(mon.rows.some(x=>x.kind==='owned_observer_child'));assert(mon.rows.some(x=>x.exitCode===0));assert.equal(mon.pending_children.length,0);assert.equal(mon.all_owned_read_callbacks_waited,true);
 const duplicate=cli(token);assert.equal(duplicate.status,1);assert(duplicate.stderr.includes('RUN_ALREADY_EXISTS'));
 const real=cli(token,'--run');assert.equal(real.status,1);assert(real.stderr.includes('ACTUAL_GO_FALSE_OR_DIAGNOSTIC_PROOF'));
 for(const [name,code] of [['unready','UNREADY'],['pause','PAUSED'],['read-error','BEADS_READ_ERROR'],['expired-monitor','PROCESSING_DEADLINE'],['undispatched','DIAGNOSTIC_UNDISPATCHED']])failure(name,{gate_case:name},code);
 failure('expired-proof',{processing_deadline_UTC:'2026-10-01T22:00:00Z'},'PROCESSING_DEADLINE');
 failure('foreign-review',{acceptancePatch:{review_issue:'quoridor-4lc.76'}},'SUBJECT_REVIEW_MEANING');
 failure('same-review',{acceptancePatch:{review_issue:'quoridor-4lc.77'},freezePatch:{review_issue:'quoridor-4lc.77'}},'SUBJECT_REVIEW_MEANING');
 failure('foreign-subject',{acceptancePatch:{subject_issue:'quoridor-4lc.75'}},'SUBJECT_REVIEW_MEANING');
 failure('foreign-bundle',{freezePatch:{bundle:{}}},'BUNDLE_ENTRY');
 const partialId=prefix+'-partial',partialToken=make(partialId,{gate_case:'after-public-pause'}),partial=cli(partialToken);assert.equal(partial.status,0,partial.stderr);
 const q=read(partialId,'driver-result').result;assert.equal(q.stopReason,'PAUSED');assert.equal(q.audit.backend_dispatches,1);assert.equal(q.audit.public_responses,1);assert.equal(q.actual_games,0);assert.equal(q.audit.completed_games,0);assert.equal(q.score.L,null);assert(read(partialId,'driver-monitor-stop').owned_read_children_zero);
 const missing=cli(null,'--run');assert.equal(missing.status,1);assert(missing.stderr.includes('EXPLICIT_TOKEN_FILE_REQUIRED'));
 const out={pass:true,NN:0,Chromium:0,real_games:0,holdout:0,actual_go:false,positive_audit:r.audit,partial_audit:q.audit,rows,diagnostic_proof_is_not_research_acceptance:true};
 fs.writeFileSync(P.A+'/'+prefix+'-driver-gates.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify({pass:true,cases:rows.length,positive:r.audit}));
}
main().catch(e=>{fs.writeFileSync(P.A+'/'+prefix+'-driver-failure.json',JSON.stringify({message:e.message,stack:e.stack,rows},null,2)+'\n');console.error(e);process.exitCode=1});
