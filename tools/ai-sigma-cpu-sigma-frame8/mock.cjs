'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const {script}=require('./adapters.cjs');
const ROOT=path.resolve(__dirname,'../..');
async function main() {
  const context={console,structuredClone,JSON,Number,Math,globalThis:null};context.globalThis=context;
  vm.runInNewContext(script('checkpoint'),context);
  let created;
  const cp={action:null,terminal_value:1,policy_fallbacks:0,value_fallbacks:0,simulations:0,nn_calls:0,root_edges:[]};
  const b={create:r=>(created=r,1),free:()=>{},call:r=>r.op==='raw'?{effective_legal:[],terminal:{value:1}}:r.op==='begin'?{done:true}:cp,e:{memory:{buffer:{byteLength:1}}}};
  const result=await context.runOwned({generation:1,request_id:'seed2098',prefix:[],seed:2098,simulations:4096,max_nodes:512,max_depth:24},{b,epoch:()=>10,yieldTask:async()=>{},getGeneration:()=>1});
  if(created.seed!==2098||result.owned.identity.seed!==2098)throw Error('SEED_TO_ABI');
  const old=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/resume-20261002/PLAYER-WORKERS/runs/p112-functional-r1/browser-result.json')).rows[0];
  const identity=structuredClone(old.identity);identity.limits.seed=2098;identity.t0_ms=1000;identity.deadline_ms=1500;identity.commit_cutoff_ms=1402;
  const latest=old.diagnostic.validated_cp;
  vm.runInNewContext(script('cache'),context);
  const snapshot={kind:'snapshot',identity,producer_identity:identity,sequence:1,owned:{identity:{request_id:identity.request_id,generation:identity.generation,fixture:null,prefix:identity.prefix,seed:2098,simulations:4096,max_nodes:512,max_depth:24},cp:latest,completed_at:1001,completed_token:1,completed_NN:latest.nn_calls,NN_attempts:latest.nn_calls,pending_token:null},value:old.diagnostic.numeric[0].value,sent_ms:1002};
  const expected={legal:latest.root_edges.map(e=>e[0]),terminal:null};
  const receiver=new context.SnapshotCache(identity,expected,()=>1003);
  if(!receiver.receive(snapshot))throw Error('SEED2098_CACHE '+JSON.stringify(receiver.events));
  const wrong=structuredClone(snapshot);wrong.owned.identity.seed=1979;
  const foreign=new context.SnapshotCache(identity,expected,()=>1003);
  if(foreign.receive(wrong)||foreign.events[0].error!=='OWNED_IDENTITY')throw Error('FOREIGN_SEED_ACCEPTED');
  console.log(JSON.stringify({seed_ABI:created.seed,completed_identity_seed:result.owned.identity.seed,cache_seed2098:true,foreign_seed1979_rejected:true,NN:0}));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
