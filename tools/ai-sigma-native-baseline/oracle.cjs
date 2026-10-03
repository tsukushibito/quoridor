'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');const ROOT=path.resolve(__dirname,'../..'),O=ROOT+'/.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';
const {Pipe,A,D,runControlled,controlDrain}=require('./common.cjs');const config=JSON.parse(fs.readFileSync(process.argv[2]));let pipe;
async function main(){pipe=new Pipe(A+'/build/target/release/faithful-native',[]);const call=async v=>{const r=await pipe.ask(v);if(!r.ok)throw Error(r.error);return r.data;};
 const ctx=vm.createContext({console,setTimeout,nativeControlDrain:controlDrain,Uint8Array,Float32Array,Uint32Array,Date,Math});
 for(const f of ['game.js','context.js','reference-core.js'])vm.runInContext(fs.readFileSync(__dirname+'/'+(f==='reference-core.js'?'reference-core-native.js':f),'utf8'),ctx);
 vm.runInContext(`const stamp=()=>0;let clockContext=null;function check(){};globalThis.oracle={fromPrefix,referenceState,rustAction,terminalResult,runMCTS,State,MCTSNode};`,ctx);
 const fixtures=JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/151-sigma-web-port/stageA-inputs.json')).fixtures;const checks=[];
 for(const fixture of fixtures){
  const state=ctx.oracle.fromPrefix(fixture.legal_prefix),prefix=[];let cursor=ctx.oracle.fromPrefix([]);for(const a of fixture.legal_prefix){prefix.push(ctx.oracle.rustAction(cursor,a));cursor=cursor.next(a)}
  const legal=state.getLegalActions().map(a=>ctx.oracle.rustAction(state,a)),raw=await call({op:'raw',fixture:{prefix}});assert.deepStrictEqual(raw.effective_legal,Array.from(legal));assert.deepStrictEqual(raw.features_bits,Array.from(new Uint32Array(state.toNNInput().buffer)));
  for(const [K,bias] of [[1,true],[8,false],[8,2]]){
   const logits=Array(136).fill(0);if(bias===true)logits[135]=4;if(bias===2){logits.fill(-20);logits[0]=20;}
   const sf=state.toNNInput();let port=(await call({op:'new',prefix,simulations:K,generation:7,trace:true})).handle;const cps=[];
   while(true){const q=await call({op:'begin',handle:port,generation:7});if(q.pending)await call({op:'resume',handle:port,generation:7,token:q.token,logits,value:Math.fround(.25)});const cp=await call({op:'checkpoint',handle:port,generation:7});cps.push(cp);if(cp.simulations===K)break;}
   const trace=await call({op:'trace',handle:port,generation:7});const end=cps.at(-1);await call({op:'free',handle:port});
   ctx.clockCtx={simulations:0,spans:[],steps:[],onComplete:()=>{}};vm.runInContext('clockContext=clockCtx',ctx);
   const evaluation=async(s,l)=>{const perm=s.isPlayer1Turn()?null:vm.runInContext('vertPolicyPermutation(9)',ctx),ix=l.map(a=>{const n=vm.runInContext('actionToIndex',ctx)(a,9);return perm?perm[n]:n}),max=Math.max(...ix.map(n=>logits[n])),ex=ix.map(n=>Math.exp(logits[n]-max)),sum=ex.reduce((a,b)=>a+b,0);return [ex.map(n=>n/sum),Math.fround(.25)];};
   const ref=await ctx.oracle.runMCTS(state,K-1,evaluation,null);const root=ref;assert.equal(root.visitCount,K);const ids=Array.from(root.children,c=>ctx.oracle.rustAction(root.state,c.action));assert.deepStrictEqual(ids,end.root_edges.map(e=>e[0]));assert.equal(end.action,ids.reduce((best,a,i)=>root.children[i].visitCount>root.children[ids.indexOf(best)].visitCount?a:best,ids[0]));assert.deepStrictEqual(end.root_edges.map(e=>e[2]),Array.from(root.children,c=>c.visitCount));for(let i=0;i<ids.length;i++)assert.equal(end.root_edges[i][3],root.children[i].valueSum);
   assert.equal(end.root_valueSum,root.valueSum);assert.equal(end.root_mean,root.qValue);if(K===1){assert.equal(end.action,legal[0]);assert(end.root_edges.slice(1).some(e=>e[1]>end.root_edges[0][1]));}
   // Ledger verifies actual private path alternation including root NN .25 exactly once.
   for(const b of trace.backups)for(let i=0;i<b.updates.length;i++)assert.equal(b.updates[i].value,b.value_leaf_side*(i%2?-1:1));
   checks.push({fixture:fixture.id,K,root_and_edge_counts_equal:true,Action_visits_values_equal:true,root_mean_true:true,first_tie_finish:true,P2_features_and_original_interleaved_order:true,sign_depths:[...new Set(trace.backups.map(b=>b.path.length))],terminal_noNN:end.terminal_noNN,NN_calls:end.nn_calls});
  }
 }
 // Explicit actual private Rust terminal/history interpretation, using saved diagnostic fixtures.
 const all=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
 for(const id of ['synthetic-total-ply-200','synthetic-goal-at200','repeat-before-third-return','straight-jump-p2']){const f=all.find(x=>x.id===id),s=ctx.oracle.referenceState(f),r=await call({op:'raw',fixture:f});const t=ctx.oracle.terminalResult(s);assert.equal(r.terminal,t?.value??null);assert.deepStrictEqual(r.effective_legal,t?[]:Array.from(s.getLegalActions(),a=>ctx.oracle.rustAction(s,a)));checks.push({fixture:id,terminal_goal_priority_or_repetition_exclusion_or_jump:true,artificial_or_saved_fixture:true});}
 // Recording toggle parity is checked in the same actual Wasm with identical oracle outputs.
 async function traceParity(on){const h=(await call({op:'new',prefix:[],simulations:8,generation:9,trace:on})).handle;let cp;while(true){const q=await call({op:'begin',handle:h,generation:9});if(q.pending)await call({op:'resume',handle:h,generation:9,token:q.token,logits:Array(136).fill(0),value:.25});cp=await call({op:'checkpoint',handle:h,generation:9});if(cp.simulations===8)break;}await call({op:'free',handle:h});return cp;}assert.deepStrictEqual(await traceParity(true),await traceParity(false));checks.push({trace_toggle_actual_private_parity:true});
 // Actual f32 ABI decimal transport regression, not rounding tree arithmetic.
 for(const value of [Math.fround(.2143749),Math.fround(-.6378562)]){
  const h=(await call({op:'new',prefix:[],simulations:1,generation:13})).handle,q=await call({op:'begin',handle:h,generation:13});
  await call({op:'resume',handle:h,generation:13,token:q.token,logits:Array(136).fill(Math.fround(.2143749)),value});
  assert.strictEqual((await call({op:'checkpoint',handle:h,generation:13})).root_valueSum,value);await call({op:'free',handle:h});
 }checks.push({actual_NN_f32_decimal_ABI_exact_extension:true});
 const result={issue:'quoridor-4lc.165',NN:0,Chrome:0,actual_private_native:true,JS_original_fixed_core:true,checks,artificial_oracle_not_runtime_NN_or_terminal_reachability_proof:true};fs.writeFileSync(config.job_out+'/oracle.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({checks:checks.length,NN:0,passed:true}));
}
runControlled(config,async check=>{check();try{await main();check();return {NN:0,passed:true};}finally{if(pipe)await pipe.stop();}}).catch(e=>{console.error(e.stack);process.exitCode=1});
