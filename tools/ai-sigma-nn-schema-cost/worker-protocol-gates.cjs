'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),N=require('./numeric.cjs');
const ROOT=path.resolve(__dirname,'../..'),OUT=ROOT+'/.artifacts/ai-sigma/continuation-20261001/SIGMA-NN-SCHEMA-COST';
const fixtures=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures;
const refs=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json')),rows=[];
let captured,aCalls=0,bCalls=0;
const ctx=vm.createContext({console,performance:require('perf_hooks').performance,TextEncoder,structuredClone,
 postMessage:d=>{captured=d},setTimeout,clearTimeout});
ctx.importScripts=(...paths)=>{for(const p of paths){
 if(p==='/ort/ort.min.js')continue; // no runtime/model factory is executed in phaseA
 const file=p==='/numeric.js'?'numeric.cjs':p==='/wrapper.js'?'wrapper.cjs':p.slice(1);
 vm.runInContext(fs.readFileSync(__dirname+'/'+file,'utf8'),ctx,{filename:file});
}};
vm.runInContext(fs.readFileSync(__dirname+'/worker.js','utf8'),ctx,{filename:'worker.js'});
function input(f){return {features_bits:N.bits(f.raw_features_float32),raw_legal:N.expected(f),
 effective_legal:f.terminal.side_to_move_value===null?N.expected(f):[],turn:f.board.turn,terminal:f.terminal.side_to_move_value}}
let current;
ctx.fakeA={alive:new Set([1]),diagnose(f){aCalls++;const ref=refs.find(x=>x.id===f.id),r=input(f);delete r.turn;delete r.terminal;
 return {...r,id:f.id,classification:f.classification,policy_logits:ref.policy_logits.slice(),value:ref.value,
 raw_prior:N.rawPriors(f,ref.policy_logits),search:[]}},drop(){this.alive.clear()}};
ctx.fakeB={call(q){return q.op==='raw'?input(q.fixture):{priors:N.rawPriors(q.fixture,q.logits)}},
 async infer(bits){bCalls++;assert.deepEqual(bits,N.bits(current.raw_features_float32));const ref=refs.find(x=>x.id===current.id);
 return {logits:ref.policy_logits.slice(),value:ref.value,nn_ms:0,spans:{run_start_ms:0,run_end_ms:0}}},async drop(){}};
vm.runInContext('A=fakeA;B=fakeB',ctx);
async function request(d){captured=null;await ctx.onmessage({data:d});assert(captured);assert.equal(captured.id,d.id);
 assert.equal(captured.ok,true,JSON.stringify(captured.error));return captured.result}
async function main(){
 let id=0;
 for(const fid of ['initial-p1','asym-hv-p2','synthetic-total-ply-200']){
  current=fixtures.find(x=>x.id===fid);const ref=refs.find(x=>x.id===fid);
  await request({id:++id,kind:'prepare',fixture:current});
  for(const side of ['A','B']){const r=await request({id:++id,kind:'call',side,fixture:current,ref});
   rows.push({id:fid,side,numeric_gate:r.numeric_gate,count:r.count,formatted_shape:Object.keys(JSON.parse(r.formatted_json)),
    kind:'NN0 injected fake evaluators using fixed reference, not actual NN'});}
 }
 const drop=await request({id:++id,kind:'drop'});assert.equal(aCalls,3);assert.equal(bCalls,3);
 assert.equal(drop.after.active,0);assert.equal(drop.after.A_handles,0);assert.equal(drop.after.count.raw_feature_calls,6);
 assert.equal(drop.after.count.search_calls,0);
 fs.writeFileSync(OUT+'/same-worker-protocol-gates.json',JSON.stringify({pass:true,actual_NN:0,Chromium:0,
  model_load:0,worker_dispatch_cases:rows,fake_counts:{aCalls,bCalls},drop,
  fake_model_drop_is_not_actual_ownership_evidence:true},null,2)+'\n');
 console.log(JSON.stringify({pass:true,call_dispatch:6,prepare_feature_only:3,drop_protocol:1,NN:0}));
}
main().catch(e=>{console.error(e);process.exitCode=1});
