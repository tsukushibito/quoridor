'use strict';
const fs=require('fs');
const path=require('path');
const assert=require('assert/strict');
const A=require('./arena.cjs');
const N=require('../ai-sigma-actual-boundary-repair/numeric-order.cjs');
const read=p=>JSON.parse(fs.readFileSync(p));
const lines=p=>fs.existsSync(p)?fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
const stats=values=>{
 const a=values.filter(Number.isFinite).sort((a,b)=>a-b);
 return a.length?{n:a.length,min:a[0],median:a.length%2?a[(a.length-1)/2]:(a[a.length/2-1]+a[a.length/2])/2,max:a.at(-1)}:{n:0};
};
const fixtures=A.fixtures();
const refs=read(A.ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json');
function analyze(run) {
 const dir=A.OUT+'/'+run;
 const config=read(dir+'/config.json');
 const summary=read(dir+'/summary.json');
 const rows=lines(dir+'/turns.jsonl');
 const publicRows=lines(dir+'/public.jsonl');
 const byId=new Map(publicRows.map(r=>[r.identity.request_id,r]));
 const backend=dir+'/real-'+run+'-session1';
 const gates=[];
 for(let index=0;index<rows.length;index++) {
  const row=rows[index];
  const saved=byId.get(row.request_id);
  assert(saved);
  const {identity,response}=saved;
  assert.equal(response.stamp_ms,row.public_stamp_ms);
  assert.equal(response.elapsed_ms,row.public_elapsed_ms);
  assert.equal(response.referee_verified,true);
  assert.equal(row.tail_condition,'cooperative');
  assert(row.owned_zero.handles===0&&row.owned_zero.activeNN===0&&row.owned_zero.live_searches===0);
  if(index)assert(row.t0_ms>=rows[index-1].stop_ACK_ms);
  const finished=read(backend+'/public-'+row.request_id+'.json');
  assert.deepEqual(finished.response,response,'PUBLIC_CHANGED_AFTER_FINISH');
  if(response.accepted)assert.deepEqual(JSON.parse(JSON.stringify(A.J.validate(identity.legal_prefix,response.action))),response.referee_action);
  for(const binding of row.bindings??[])if(binding.accepted&&binding.kind==='snapshot')assert(binding.last_gate.validated_cache_ms<identity.commit_cutoff_ms);
  const fixture=fixtures.find(f=>JSON.stringify(f.legal_prefix)===JSON.stringify(identity.legal_prefix));
  const reference=fixture?refs.find(r=>r.id===fixture.id):undefined;
  if(row.root_numeric)gates.push({id:row.request_id,engine:row.engine,...N.check({engine:row.engine,state:A.J.state(identity.legal_prefix),numeric:row.root_numeric,cp:row.root_cp,reference})});
  else gates.push({id:row.request_id,missing_numeric:true,terminal:A.J.terminalResult(A.J.state(identity.legal_prefix))});
 }
 for(const game of summary.games) {
  if(game.result.prefix)A.J.ids(game.result.prefix);
  if(game.result.terminal)assert.deepEqual(JSON.parse(JSON.stringify(A.J.terminalResult(A.J.state(game.result.prefix)))),game.result.terminal);
 }
 const counts={public:rows.length,accepted:rows.filter(r=>r.accepted).length,late:publicRows.filter(r=>r.response.late).length,missing_completed_cp:rows.filter(r=>!r.checkpoint).length,accepted_cache_before_cutoff_caller_marker_after:rows.reduce((n,r)=>n+(r.bindings??[]).filter(b=>b.accepted&&b.kind==='snapshot'&&b.node_validation_finished_ms>=byId.get(r.request_id).identity.commit_cutoff_ms).length,0),hand_NN:summary.NN_hand,startup_NN:summary.startup.root_NN,fixed_golden_root_references:gates.filter(g=>g.fixed_reference).length,dynamic_root_gates:gates.filter(g=>!g.fixed_reference&&!g.missing_numeric).length,features_bits:gates.filter(g=>!g.missing_numeric).length*648,NN_elements:gates.filter(g=>!g.missing_numeric).length*137,prior_elements:gates.reduce((n,g)=>n+(g.priors??0),0)};
 const engines=['candidate','reference'].map(engine=>{
  const own=rows.filter(r=>r.engine===engine);
  return {engine,public:own.length,public_elapsed_ms:stats(own.map(r=>r.public_elapsed_ms)),ACK_cause_wall_ms:stats(own.map(r=>r.cause_window_ms)),ACK_wall_over500:own.filter(r=>r.budget_breach).length,Worker_stop_classes:own.reduce((s,r)=>(s[r.Worker_stop_class]=(s[r.Worker_stop_class]??0)+1,s),{}),Worker_stop_upper_elapsed_ms:stats(own.map(r=>r.Worker_stop_interval?.late_ms-r.t0_ms)),after402_NN_starts:own.reduce((n,r)=>n+r.NN_start_after_cutoff_worker,0),post_public_NN_definite:own.reduce((n,r)=>n+r.post_public_NN_start_definite,0),post_public_NN_possible:own.reduce((n,r)=>n+r.post_public_NN_start_possible,0),last_API_to_Worker_stop_ms:stats(own.map(r=>r.last_API_to_Worker_stop_ms)),stop_to_Node_lower_ms:stats(own.map(r=>r.stop_to_Node_interval?.lo_ms)),stop_to_Node_upper_ms:stats(own.map(r=>r.stop_to_Node_interval?.hi_ms)),Node_receive_to_confirm_ms:stats(own.map(r=>r.Node_received_to_confirm_ms)),public_Judge_clone_UTF8_ms:stats(own.map(r=>r.shared_final_Judge_clone_UTF8_ms)),public_log_ms:stats(own.map(r=>r.shared_public_log_ms)),inspection_ms:stats(own.map(r=>r.shared_diagnostic_inspection_ms)),CPU:'retained same-identity observed lower bound; final exited-child counter unknown'};
 });
 const result={issue:config.issue,run,git:config.git,game_starts:summary.game_starts,W:summary.W,D:summary.D,L:summary.L,unfinished:summary.unfinished_games,natural_goal_games:summary.games.filter(g=>g.result.terminal?.winner).length,responsibility_games:summary.games.filter(g=>g.result.kind==='engine_loss').length,counts,engines,numeric_gates:gates,primary:summary.primary,secondary:summary.secondary,formal_fairness:false,formal_NI:false,limits:['ACKcause wall is not engine compute time','API await is not inner kernel time','clock intervals overlap; do not sum overlapping spans','dynamic root softmax/shape is not fixed-golden NN or all-deep-node equivalence','CPU observed lower bound; exited final child counter missing','same telemetry/FIFO; no payload factor change','current absence is not natural exit or all-period proof']};
 fs.writeFileSync(dir+'/analysis.json',JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({...result,numeric_gates:undefined}));
 return result;
}
for(const run of process.argv.slice(2))analyze(run);
