'use strict';
require('./checkpoint.js');const {runOwned,validateDelivery}=globalThis;const assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const RUN=path.resolve(__dirname,'../../.artifacts/ai-sigma/runs/SIGMA-ORT-CHECKPOINT');
const expected={generation:7,terminal_value:null,action:7,simulations:1,nodes_count:2,nodes:2,edges_count:2,max_depth:1,arena_bytes:99,high_water:99,cap:false,policy_fallbacks:0,value_fallbacks:0,nn_calls:1,root_edges:[[7,1065353216,1,1048576000]],tree:[{history:[['owned-root',1]],visits:1}]};
async function sample(name,setup={}){let now=0,gen=7,n=0,completed=0,free=0,cancel=0,calls=0,partial=false;
 const b={e:{memory:{buffer:{byteLength:4096}}},create:()=>1,free:h=>{assert.equal(h,1);free++},infer:async()=>{calls++;if(setup.nnerror&&completed>=1)throw Error('NN_ERROR');return{logits:Array(136).fill(0),value:.25,nn_ms:5}},call:v=>{
 if(v.op==='raw')return{raw_legal:[7],effective_legal:[7],terminal:null};
 if(v.op==='begin'){partial=true;n++;return{pending:true,token:n,features_bits:Array(648).fill(0)}}
 if(v.op==='resume'){if(setup.token&&completed>=1)throw Error('INVALID_TOKEN');if(setup.nan&&completed>=1)throw Error('OUTPUT_FINITE');completed++;partial=false;return{done:setup.single}}
 if(v.op==='snapshot'||v.op==='checkpoint'){assert.equal(partial,false);return{...expected,simulations:completed,nodes_count:partial?999:2,nn_calls:completed,tree:[{history:[['owned-root',1]],visits:completed}]}}
 if(v.op==='cancel'){cancel++;return{discarded:true}}
 throw Error('OP');}};
 const r=await runOwned({fixture:{id:'mock-root'},generation:7,request_id:8,T_ms:500,g_ms:91,t0:0,capture_tree:true,capture_trace:true}, {b,epoch:()=>now,getGeneration:()=>gen,notify:()=>{},yieldTask:async()=>{if(setup.before!=null&&(setup.cross==null||n>=2))now=setup.before},hook:async(phase,state)=>{
 if(phase==='after_begin'&&n===(setup.nocp?1:2)){if(setup.cross!=null)now=setup.cross;if(setup.cancel)gen++;if(setup.hard)throw Error('HARD_ERROR');if(setup.deadline)now=500}
 if(phase==='before_checkpoint'&&setup.checkpointlate&&completed===2)now=500;
 if(phase==='before_return'&&setup.returnlate)now=500;
 }});
 assert.equal(free,1);assert.equal(r.live_searches,0);
 if(setup.ok){assert.equal(r.error,null);const k=setup.expectedSims??1;assert.deepEqual(r.cp,{...expected,simulations:k,nn_calls:k,tree:[{history:[['owned-root',1]],visits:k}]});assert.equal(r.calls,k);assert.equal(r.completed_NN,k);assert.equal(r.owned.identity.request_id,8);assert.equal(Object.isFrozen(r.owned.cp),true);assert.equal(r.owned.completed_token,k);assert.equal(validateDelivery(r,{generation:7,request_id:8,now:499,deadline:500,legal:[7]}),true);
  for(const change of [{now:500},{generation:8},{request_id:9},{legal:[8]},{fixture:{id:'foreign'}},{prefix:[123]},{clock:()=>500}])assert.equal(validateDelivery(r,{generation:7,request_id:8,now:499,deadline:500,legal:[7],...change}),false);
 }else{assert.notEqual(r.error,null);assert.equal(r.cp,null);assert.equal(r.owned,null)}
 return{name,now,free,cancel,NN_attempts:calls,result:r};}
(async()=>{const cases=[['before_exact',{before:409,ok:true}],['before_after',{before:409.001,ok:true}],['begin_before',{cross:408.999,before:409,expectedSims:2,ok:true}],['begin_exact',{cross:409,ok:true}],['begin_after',{cross:409.001,ok:true}],['first_no_cp',{nocp:true,cross:409}],['NNerror_after_cp',{nnerror:true}],['NaN_after_cp',{nan:true}],['token_after_cp',{token:true}],['cancel_after_cp',{cancel:true}],['hard_after_cp',{hard:true}],['deadline_after_begin',{deadline:true}],['checkpoint_late',{checkpointlate:true}],['return_late',{single:true,returnlate:true}]];
 const rows=[];for(const [name,opts]of cases)rows.push(await sample(name,opts));fs.writeFileSync(path.join(RUN,'mock-gate-final.json'),JSON.stringify({expected,rows,failures:0},null,2));console.log(JSON.stringify({cases:rows.length,failures:0}));})().catch(e=>{console.error(e);process.exitCode=1});
