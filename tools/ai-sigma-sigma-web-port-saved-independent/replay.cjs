'use strict';
// Existing Wasm and fixed NN tapes only. No ONNX session or NN evaluator is loaded.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const R=path.resolve(__dirname,'../..'),D=R+'/research-data/ai-sigma/153-sigma-web-port-saved-independent',P=R+'/.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
const rawBytes=fs.readFileSync(P+'/runs/port151-stageA-r2/browser-result.json');assert.equal(digest(rawBytes),'d37215cbc7914519ca24ab254c5e413d21e780389094faed537280a059c234d2');
const raw=JSON.parse(rawBytes),fixtures=JSON.parse(fs.readFileSync(R+'/research-data/ai-sigma/151-sigma-web-port/stageA-inputs.json')).fixtures;
const clean=x=>JSON.parse(JSON.stringify(x));
let maxPrior=0,signedZero=0;function numericTraceEqual(a,b){if(typeof a==='number'){assert(a===b);if(!Object.is(a,b))signedZero++;return;}if(a===null||typeof a!=='object'){assert.strictEqual(a,b);return;}assert.deepStrictEqual(Object.keys(a),Object.keys(b));for(const k of Object.keys(a))numericTraceEqual(a[k],b[k]);}
function cpCompare(cp,saved){
 for(const k of ['action','root_visits','root_valueSum','root_mean'])assert.deepStrictEqual(cp[k],saved[k],k);
 assert.equal(cp.root_edges.length,saved.root_edges.length);
 cp.root_edges.forEach((e,i)=>{let z=saved.root_edges[i];for(const j of [0,2,3])assert.strictEqual(e[j],z[j]);let d=Math.abs(e[1]-z[1]);maxPrior=Math.max(maxPrior,d);assert(d<=1e-4+1e-4*Math.abs(z[1]));});
}
async function main(){
 const bytes=fs.readFileSync(P+'/build/faithful.wasm');assert.equal(digest(bytes),'500181795b373f69f6f2214ee1a77e12767e2f342e15a56ab5e27d0a0453f2c2');
 const e=(await WebAssembly.instantiate(bytes,{})).instance.exports;
 function call(obj){let h=0,o=0;try{const b=Buffer.from(JSON.stringify(obj));h=e.ort_buffer(b.length);new Uint8Array(e.memory.buffer,e.ort_ptr(h),b.length).set(b);o=e.ort_call(h);let result=JSON.parse(Buffer.from(new Uint8Array(e.memory.buffer,e.ort_ptr(o),e.ort_len(o))).toString());assert(result.ok,result.error);return result.data;}finally{if(h)e.ort_free(h);if(o)e.ort_free(o);}}
 const c=vm.createContext({setTimeout,Float32Array,Uint32Array,Uint8Array,Math,console});
 vm.runInContext('let clockContext=null;function stamp(){return 0}function check(){}',c);
 const scripts={};for(const f of ['game.js','context.js','reference-core.js']){const b=fs.readFileSync(R+'/tools/ai-sigma-actual-boundary-repair/'+f);scripts[f]=digest(b);vm.runInContext(b.toString(),c);}
 vm.runInContext('globalThis.saved={fromPrefix,rustAction,actionToIndex,vertPolicyPermutation,runMCTS};globalThis.setClock=x=>clockContext=x;',c);
 const results=[];
 for(const id of ['asym-hv-p2','straight-jump-p2']){
  const f=fixtures.find(f=>f.id===id),a=raw.rows.find(r=>r.fixture_id===id&&r.engine==='candidate'),b=raw.rows.find(r=>r.fixture_id===id&&r.engine==='reference');
  // Derive the Rust replay prefix through the shared RuleA bridge; its independence limit is explicit.
  let state=c.saved.fromPrefix([]),prefix=[];for(const action of f.legal_prefix){prefix.push(c.saved.rustAction(state,action));state=state.next(action);}
  const h=call({op:'new',prefix,simulations:32,generation:71,trace:true}).handle;let count=0;
  try{
   while(count<32){const q=call({op:'begin',handle:h,generation:71});assert(q.pending,'terminal/new cap would invalidate fixed tape');const n=a.numeric[count];
    for(const k of ['key','turn','ply','features_bits','legal','path','node_index'])assert.deepStrictEqual(q[k],n[k],k);
    assert.deepStrictEqual(q.history.slice().sort(),n.history.slice().sort());
    call({op:'resume',handle:h,generation:71,token:q.token,logits:n.policy_logits,value:n.value});cpCompare(call({op:'checkpoint',handle:h,generation:71}),a.CPs[count]);count++;
   }
   numericTraceEqual(call({op:'trace',handle:h,generation:71}),a.trace);
  }finally{assert.equal(e.ort_free(h),1);}
  // Actual fixed JS core: supply the saved same-state logits/value, capturing each root finish.
  let ni=0,ci=0;const tape=b.numeric;
  c.setClock({simulations:0,spans:[],steps:[],onComplete(root){const edges=Array.from(root.children,z=>[c.saved.rustAction(root.state,z.action),z.prior,z.visitCount,z.valueSum]);let best=0;for(let i=1;i<edges.length;i++)if(edges[i][2]>edges[best][2])best=i;cpCompare({action:edges[best][0],root_visits:root.visitCount,root_valueSum:root.valueSum,root_mean:root.qValue,root_edges:edges},b.CPs[ci++]);}});
  const evaluation=async(s,legal)=>{const n=tape[ni++];assert(n,'NN tape exhausted');assert.equal(s._positionKey(),n.key);assert.equal(s.depth,n.ply);assert.equal(s.isPlayer1Turn()?0:1,n.turn);assert.deepStrictEqual(Array.from(new Uint32Array(s.toNNInput().buffer)),n.features_bits);assert.deepStrictEqual(clean([...s.position_history].sort()),n.history.slice().sort());assert.deepStrictEqual(Array.from(legal,a=>c.saved.rustAction(s,a)),n.legal);
   const perm=n.turn?c.saved.vertPolicyPermutation(9):null,ls=Array.from(legal,a=>{const i=c.saved.actionToIndex(a,9);return n.policy_logits[perm?perm[i]:i];});let mx=Math.max(...ls),sum=0,ex=ls.map(v=>Math.exp(v-mx));for(const x of ex)sum+=x;return [ex.map(x=>x/sum),n.value];};
  const root=await c.saved.runMCTS(state,31,evaluation,null);assert.equal(ni,32);assert.equal(ci,32);assert.equal(root.visitCount,32);
  results.push({id,actual_Wasm_CP32_trace_arithmetic_equal:true,actual_JS_CP32_saved_state_exact:true,saved_tape_requests:32,new_NN:0});
 }
 const out={issue:'quoridor-4lc.153',UTC:new Date().toISOString(),actual_Wasm:true,actual_JS_VM:true,NN:0,Chrome:0,model_load:0,build:0,results,signed_zero_numeric_differences:signedZero,max_prior_abs_difference:maxPrior,binary_SHA256:digest(bytes),shared_RuleA_limit:true,scripts,teacher_NN_correctness_not_reexecuted:true};
 fs.writeFileSync(D+'/replay.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify(out));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
