'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const T=path.resolve(__dirname,'../ai-sigma-actual-boundary-repair');
const J=require(T+'/judge.cjs'),G=require(T+'/game-loop.cjs'),C=require(T+'/caller.cjs'),F=require(T+'/final-envelope.cjs'),{freeze}=require(T+'/early-cache.cjs');
const ROOT=path.resolve(__dirname,'../..'),OUT=ROOT+'/.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA';
const MODEL='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d';
const fixtures=()=>JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
const clock={now:C.now,wall:Date.now,delay:(ms,fn)=>setTimeout(fn,ms),clear:clearTimeout};
function validate(c){
 assert.equal(c.issue,'quoridor-4lc.93');assert.equal(c.run_kind,'exploratory-diagnostic');assert.equal(c.diagnostic,true);assert.equal(c.actual_go,false);assert.equal(c.holdout,false);
 assert(/^[A-Za-z0-9_-]+$/.test(c.run_id));assert.equal(c.model_sha256,MODEL);assert.equal(c.seed,1979);assert.deepEqual(c.affinity,[2]);assert.equal(c.NNthreads,1);
 assert.deepEqual(c.clock,{T:500,reserve:89,commit:9,cutoff:402,seal:411});assert(Number.isFinite(Date.parse(c.processing_deadline))&&Date.parse(c.processing_deadline)<=Date.parse('2026-10-02T05:39:12Z'));
 assert(['golden','four-ply','pair'].includes(c.stage));assert.equal(c.games_before,Number(c.games_before));assert(c.games_before>=0&&c.games_before+(c.stage==='pair'?2:0)<=8);
 const allowed=['initial-p1','asym-hv-p2','straight-jump-p2'];assert(allowed.includes(c.fixture_id));const f=fixtures().find(f=>f.id===c.fixture_id);assert(f&&Array.isArray(f.legal_prefix));assert.equal(c.prefix_sha256,J.hash(f.legal_prefix));J.ids(f.legal_prefix);assert(!J.terminalResult(J.state(f.legal_prefix)));
 if(c.stage==='pair')assert.deepEqual(c.candidate_color_order,[1,2]);return f;
}
function bounded(p,ms,label){let t;return Promise.race([p,new Promise((_,reject)=>t=setTimeout(()=>reject(Object.assign(Error(label),{code:label})),ms))]).finally(()=>clearTimeout(t));}
function ticks(rows){return rows.reduce((n,r)=>n+r.utime_ticks+r.stime_ticks,0);}
async function execute(config,{createBackend,monitor,save,append,diagnosticMock=false}){
 const fixture=validate(config),events=[],games=[],turns=[];let backend=null,generation=0,lastAck=null,signal=null,primary=null,secondary=[],startup=null,gameStarts=0,pendingGame=null;
 const signalFn=n=>{signal=n};const interrupt=()=>signalFn('SIGNAL');process.once('SIGINT',interrupt);process.once('SIGTERM',interrupt);
 const guard=()=>{if(signal)throw Error(signal);monitor.check();if(Date.now()>=Date.parse(config.processing_deadline))throw Error('PROCESSING_DEADLINE');};
 async function choose(engine,input,meta={}){
  guard();if(lastAck&&!(lastAck.handles===0&&lastAck.activeNN===0&&lastAck.live_searches===0))throw Error('OLD_WORK_NOT_ZERO_FRESH_FORBIDDEN');
  // Immutable input is available now, adapter/replay/validation follow this t0.
  const t0=clock.now(),cpu0=backend.cpuSnapshot?.()??[],nodeCPU0=process.cpuUsage();let context=null,id=null,sealTimer,deadlineTimer;
  let release;const publicP=new Promise(r=>release=r);let closed=false;
  function publish(r){if(closed)return;closed=true;clearTimeout(sealTimer);clearTimeout(deadlineTimer);release(r);}
  sealTimer=setTimeout(()=>{if(!context)publish({accepted:false,checkpoint:false,action:null,error:'NO_COMPLETED_SNAPSHOT',local_timeout:true})},Math.max(0,t0+411-clock.now()));
  deadlineTimer=setTimeout(()=>publish({accepted:false,checkpoint:false,action:null,error:'NO_RESPONSE_TIMEOUT',local_timeout:true}),Math.max(0,t0+500-clock.now()));
  try{const prefix=JSON.parse(JSON.stringify(input.legal_prefix)),s=J.state(prefix),ctx=J.context(s);id=freeze({engine,request_id:config.run_id+'-'+(++generation),generation,epoch:generation,fixture_id:input.id,fixture:null,legal_prefix:prefix,prefix:J.ids(prefix),key:ctx.key,history:ctx.history,model:MODEL,schema:'8x9x9-f32/136logits/value1/rust209',limits:{simulations:engine==='reference'?100000:4096,max_nodes:engine==='reference'?null:512,max_depth:engine==='reference'?null:24,seed:1979},t0_ms:t0,deadline_ms:t0+500,seal_ms:t0+411,commit_cutoff_ms:t0+402,request_token:config.run_id+'-'+generation});
   guard();context=backend.create({identity:id,meta});Promise.resolve(backend.submit(context)).then(publish,e=>publish({accepted:false,checkpoint:false,action:null,error:e.code??e.message,local_timeout:true}));
   const raw=await publicP,response=F.finalize(raw,id,clock);const publicCPU=backend.cpuSnapshot?.()??[],publicNodeCPU=process.cpuUsage(nodeCPU0);
   // Public response is fixed first. Owned NN and handles are awaited separately.
   append('public',{identity:id,response});const ack=await bounded(backend.finish(context,response),2000,'OLD_SEARCH_STOP_TIMEOUT');const ackStamp=clock.now();
   assert(ack&&ack.handles===0&&ack.activeNN===0&&ack.live_searches===0&&!ack.ownership_error);lastAck=ack;
   const ackCPU=backend.cpuSnapshot?.()??[],ackNodeCPU=process.cpuUsage(nodeCPU0);const diag=backend.inspect?await backend.inspect(context):null,inspectionEnd=clock.now();
   const priv=diag?.private,nn=priv?.NN??[],offset=diag?.clock?.worker;
   const spans=nn.map(n=>({start_early_ms:n.session_run_start_ms-(offset?.hi_ms??0),start_late_ms:n.session_run_start_ms-(offset?.lo_ms??0),end_early_ms:n.session_run_end_ms-(offset?.hi_ms??0),end_late_ms:n.session_run_end_ms-(offset?.lo_ms??0),api_await_ms:n.session_run_end_ms-n.session_run_start_ms}));
   const row={engine,request_id:id.request_id,fixture_id:id.fixture_id,ply:prefix.length,t0_ms:t0,public_stamp_ms:response.stamp_ms,public_elapsed_ms:response.stamp_ms-t0,stop_ACK_ms:ackStamp,cause_window_ms:ackStamp-t0,budget_breach:ackStamp-t0>500,residual_after_public_ms:Math.max(0,ackStamp-response.stamp_ms),owned_zero:ack,post_public_NN_start_definite:spans.filter(s=>s.start_early_ms>response.stamp_ms).length,post_public_NN_start_possible:spans.filter(s=>s.start_late_ms>response.stamp_ms).length,NN_completed:nn.length,API_spans:spans,worker_clock:offset,cpu:{tick_unit_hz:100,browser_before:cpu0,browser_public:publicCPU,browser_ACK:ackCPU,browser_public_ticks:ticks(publicCPU)-ticks(cpu0),browser_residual_ticks:ticks(ackCPU)-ticks(publicCPU),node_public_us:publicNodeCPU,node_whole_us:ackNodeCPU,node_includes_judge_log_monitor:true},shared_diagnostic_inspection_ms:inspectionEnd-ackStamp,accepted:response.accepted,action:response.action,error:response.error,checkpoint:response.checkpoint,root_cp:diag?.cp??null,root_numeric:priv?.numeric?.[0]??null,bindings:diag?.bindings??null};
   turns.push(row);append('turns',row);return response;
  }finally{clearTimeout(sealTimer);clearTimeout(deadlineTimer);}
 }
 try{guard();const start=clock.now();backend=await createBackend({session:1,clock});assert(backend.startup.ready);startup={wall_ms:clock.now()-start,root_NN:diagnosticMock?0:6,outside_first_input_clock:true,tree_history_cache_reuse:false};save('ready',startup);
  if(config.stage==='golden'){
   for(const engine of ['candidate','reference'])await choose(engine,{id:fixture.id,legal_prefix:fixture.legal_prefix});
  }else if(config.stage==='four-ply'){
   const result=await G.runGame({prefix:fixture.legal_prefix,candidateColor:1,platform:'browser',choose,clock:clock.now,maxAddedPly:4,log:r=>append('moves',r)});games.push({kind:'four-ply-diagnostic',result});assert(result.diagnostic_stop===true&&result.prefix.length===fixture.legal_prefix.length+4,'FOUR_PLY_NOT_COMPLETED');
  }else for(const color of config.candidate_color_order){guard();const index=config.games_before+games.length+1;gameStarts++;pendingGame={game:index,candidateColor:color};append('game-start',{game:index,candidateColor:color,fixture_id:fixture.id,prefix_sha256:config.prefix_sha256,seed:1979});const result=await G.runGame({prefix:fixture.legal_prefix,candidateColor:color,platform:'browser',choose,clock:clock.now,log:r=>append('moves',{game:index,...r})});games.push({game:index,candidateColor:color,result});pendingGame=null;save('games-partial',games);if(!result.complete||result.kind==='invalid_pair')break;}
 }catch(e){primary={name:e.name,code:e.code??e.message,message:e.message,stack:e.stack};save('primary',primary);if(pendingGame)games.push({...pendingGame,result:{complete:false,score:null,reason:primary.code,prefix_unavailable:true}});}finally{
  if(backend)try{const proof=await bounded(backend.stop(),15000,'OWN_CLEANUP_TIMEOUT');save('backend-stop',proof);assert(proof?.controlledPID0===true||proof?.handles===0&&proof?.activeNN===0);}catch(e){secondary.push({stage:'backend-stop',name:e.name,message:e.message,stack:e.stack});save('secondary',secondary);}
  try{await monitor.stop();}catch(e){secondary.push({stage:'monitor-stop',message:e.message});save('secondary',secondary);}process.removeListener('SIGINT',interrupt);process.removeListener('SIGTERM',interrupt);
 }
 const completed=games.filter(g=>g.game&&g.result.complete&&g.result.score!=null),summary={issue:config.issue,run_id:config.run_id,stage:config.stage,Git:config.git,diagnostic:true,diagnostic_mock:diagnosticMock,actual_go:false,holdout_sends:0,turns:turns.length,public_accepted:turns.filter(t=>t.accepted).length,budget_breaches:turns.filter(t=>t.budget_breach).length,NN_hand:turns.reduce((n,t)=>n+t.NN_completed,0),startup,games,game_starts:gameStarts,completed_games:completed.length,unfinished_games:games.filter(g=>g.game&&!g.result.complete).length,W:completed.filter(g=>g.result.score===1).length,D:completed.filter(g=>g.result.score===.5).length,L:completed.filter(g=>g.result.score===0).length,primary,secondary,formal_fairness:false,formal_NI:false};save('summary',summary);return summary;
}
async function main(){assert.equal(process.argv[2],'--config');const c=JSON.parse(fs.readFileSync(process.argv[3]));validate(c);const out=OUT+'/'+c.run_id;fs.mkdirSync(out,{recursive:false});const save=(n,x)=>fs.writeFileSync(out+'/'+n+'.json',JSON.stringify(x)+'\n'),append=(n,x)=>fs.appendFileSync(out+'/'+n+'.jsonl',JSON.stringify(x)+'\n');save('config',c);
 const {createMonitor}=require(T+'/pause-check.cjs');const monitor=createMonitor({out,subjectIssue:c.issue,deadlineUTC:c.processing_deadline,windowEndUTC:'2026-10-02T05:39:12Z'});await monitor.start();
 const result=await execute(c,{monitor,save,append,createBackend:require(T+'/real-backend.cjs').factory(c.run_id,{base:out,captureTree:false})});console.log(JSON.stringify({...result,games:result.games.map(g=>({...g,result:{...g.result,prefix_length:g.result.prefix?.length,prefix:undefined}}))}));if(result.primary||result.secondary.length)process.exitCode=1;
}
module.exports={execute,validate,clock,fixtures,ROOT,OUT,J};if(require.main===module)main().catch(e=>{console.error(e.stack);process.exitCode=1});
