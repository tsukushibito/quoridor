const assert=require('node:assert/strict'),fs=require('node:fs'),{guardTransaction,now}=require('./transaction.cjs'),G=require('./game-loop.cjs'),J=require('./judge.cjs');const RUN='../../.artifacts/ai-sigma/runs/SIGMA-PAIRED-MATCHES';
(async()=>{const rows=[];
for(const engine of ['native','candidate','reference'])for(const mode of ['valid','wrong-gen','foreign-id','unknown','null','error','no-response','exit','late','duplicate']){
 const req={request_id:engine+'-'+mode,generation:1001},t0=now(),events=[];let stops=0;
 let payload={transaction:{...req},generation:1001,data:{generation:1001},action:4};
 if(mode==='wrong-gen')payload.transaction.generation=999999;
 if(mode==='foreign-id')payload.transaction.request_id='different-prefix-token';
 if(mode==='unknown')payload={action:4};if(mode==='null')payload=null;
 if(mode==='error')payload.error='NN_ERROR';
 const send=()=>mode==='exit'?Promise.reject(Error('BACKEND_EXIT')):mode==='no-response'?new Promise(()=>{}):mode==='late'?new Promise(r=>setTimeout(()=>r({payload}),25)):Promise.resolve({payload});
 const q=await guardTransaction({engine,req,t0,T:10,send,abort:async()=>{stops++;},event:e=>events.push(e)});
 if(['valid','error','duplicate'].includes(mode))assert.equal(q.transaction_error,undefined);else assert.ok(q.transaction_error);
 if(mode==='no-response')assert.ok(q.watchdog_at_ms>=t0+10);
 if(mode==='duplicate'){const stale=await guardTransaction({engine,req:{request_id:req.request_id+'-next',generation:1002},t0:now(),T:10,send:()=>Promise.resolve({payload}),abort:async()=>{stops++;}});assert.equal(stale.transaction_error,'IDENTITY_MISMATCH');}
 rows.push({engine,mode,result:q,stops,elapsed_ms:now()-t0,events});
}
const fixtures=JSON.parse(fs.readFileSync('../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
const goal=fixtures.find(f=>f.id==='goal-win-legal-replay');const before=goal.legal_prefix.slice(0,-1),last=goal.legal_prefix.at(-1);const winner=J.terminalResult(J.state(goal.legal_prefix)).winner;
for(const color of [1,2]){const q=await G.runGame({prefix:before,candidateColor:color,platform:'browser',choose:async()=>({accepted:true,action:J.encode(J.state(before),last)})});assert.equal(q.score,color===winner?1:0);rows.push({mode:'goal_color_score',color,result:q});}
for(const error of ['NO_RESPONSE_TIMEOUT','SEARCH_ERROR'])for(const color of [1,2]){const r=await G.runGame({prefix:[],candidateColor:color,platform:'native-local',choose:async()=>({accepted:false,error})});assert.equal(r.score,color===1?0:1);rows.push({mode:'engine_loss',error,color,result:r});}
const illegal=await G.runGame({prefix:[],candidateColor:1,platform:'browser',choose:async()=>({accepted:true,action:999})});assert.equal(illegal.score,0);
assert.equal(G.terminalScore({winner:0},1),.5);
for(const id of ['synthetic-total-ply-200','synthetic-no-legal-move-draw','synthetic-goal-at200']){const f=fixtures.find(x=>x.id===id)||fixtures.find(x=>x.id==='synthetic-goal-at200');if(f){const s=J.referenceState(f);assert.ok(J.terminalResult(s));rows.push({mode:'artificial_terminal_not_reachability',id,result:J.terminalResult(s)});}}
await assert.rejects(G.runGame({prefix:goal.legal_prefix,candidateColor:1,platform:'browser',choose:()=>{throw Error('NN called')}}),/TERMINAL_INITIAL/);
const prefixes=[],retryBudget={remaining:2};let calls=0;const pair=await G.runPair({prefix:before,colorOrder:[2,1],retryBudget,correct:async()=>{},play:async(prefix,color,attempt)=>{prefixes.push({prefix,color,attempt});calls++;return calls===1?{kind:'invalid_pair',complete:false}:{complete:true,score:color===1?1:0};}});assert.equal(pair.Xi,.5);assert.equal(retryBudget.remaining,1);assert.ok(prefixes.every(p=>JSON.stringify(p.prefix)===JSON.stringify(before)));rows.push({mode:'pair_retry_same_prefix_colors',pair,prefixes});
const stuckAt=now();const stuck=await guardTransaction({engine:'native',req:{request_id:'stuck-cleanup',generation:7},t0:stuckAt,T:10,send:()=>new Promise(()=>{}),abort:()=>new Promise(()=>{})});assert.equal(stuck.transaction_error,'NO_RESPONSE_TIMEOUT');assert.ok(now()-stuckAt<78);rows.push({mode:'nonblocking_timeout_even_if_cleanup_stuck',result:stuck});
 const {pipe}=require('./arena.cjs');const backend=pipe(process.execPath,['-e','process.stdin.resume()'],'mock-process.stderr.log');await backend.abort();assert.ok(backend.child.signalCode!==null||backend.child.exitCode!==null);rows.push({mode:'SIGTERM_cleanup_already_exited',signal:backend.child.signalCode});
 fs.writeFileSync(RUN+'/mock-tests-final.json',JSON.stringify({pass:true,rows,formal_games:0,holdout_sends:0},null,2));console.log('pass',rows.length);
})().catch(e=>{console.error(e);process.exitCode=1});
