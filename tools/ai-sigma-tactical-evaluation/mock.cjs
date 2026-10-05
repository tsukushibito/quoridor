'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const ROOT = path.resolve(__dirname,'../..');
const document = JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/127-tactical-oracle/labels-and-inputs.json'));
const context = vm.createContext({console,structuredClone,document});
for (const source of ['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-tactical-oracle/checker.js','tools/ai-sigma-tactical-evaluation/tactical-main.js']) vm.runInContext(fs.readFileSync(ROOT+'/'+source,'utf8'),context);
const labels = vm.runInContext('tacticalPreflight(document)',context);
assert.equal(labels.cases.length,4);
const defects = vm.runInContext(`(()=>{
 const checks=[];
 const missing=structuredClone(document);missing.labels[0].certificate.immediate_wins_complete=false;
 try{tacticalPreflight(missing);throw Error('FALSE_PASS');}catch(e){if(e.message==='FALSE_PASS')throw e;checks.push(e.message);}
 const foreign=structuredClone(document.inputs[0]);foreign.history.pop();
 try{tacticalState(foreign);throw Error('FALSE_PASS');}catch(e){if(e.message==='FALSE_PASS')throw e;checks.push(e.message);}
 const input=document.inputs[1],certificate=document.labels[1].certificate;
 const good=tacticalLabel(input,certificate,{response:{classification:'completed_legal',body:{action:{type:'wall',x:3,y:0,orientation:'h'}}}});
 const bad=tacticalLabel(input,certificate,{response:{classification:'completed_legal',body:{action:{type:'pawn',direction:[0,1]}}}});
 const late=tacticalLabel(input,certificate,{response:{classification:'browser_late',causes:{browser_deadline_late:true}}});
 if(!good.label_verdict||bad.label_verdict!==false||late.label_verdict!==null)throw Error('RESPONSIBILITY_CLASSIFICATION');
 return {checks,good,bad,late};
})()`,context);
const adapted = require('./adapters.cjs');
for(const name of ['main','worker','producer','checkpoint','cache']) new vm.Script(adapted.script(name));
const checkpoint = vm.createContext({console});
vm.runInContext(adapted.script('checkpoint'),checkpoint);
let handles=0,calls=0,begin=0,now=0;
const cp={action:13,generation:1,simulations:1,nn_calls:1,root_edges:[[13,1,0,0]],terminal_value:null,policy_fallbacks:0,value_fallbacks:0};
const b={e:{memory:{buffer:new ArrayBuffer(65536)}},create(req){assert.equal(req.simulations,1);handles++;return 1;},call(command){
 if(command.op==='raw')return {effective_legal:[13],terminal:null};
 if(command.op==='begin'){begin++;return {pending:true,token:1,features_bits:new Array(648).fill(0)};}
 if(command.op==='resume')return {done:true};
 if(command.op==='checkpoint')return structuredClone(cp);
 throw Error('unexpected '+command.op);
},infer:async()=>{calls++;return {logits:new Array(136).fill(0),value:0,nn_ms:1};},free(){handles--;}};
(async()=>{
 const rows=[];
 const result=await checkpoint.runOwned({prefix:[],generation:1,request_id:'stress-mock',simulations:1,max_nodes:512,max_depth:24,seed:1979},{b,epoch:()=>++now,yieldTask:async()=>{},getGeneration:()=>1,completed:x=>rows.push(x)});
 assert.equal(result.error,null);assert.equal(result.cp.simulations,1);assert.equal(calls,1);assert.equal(begin,1);assert.equal(handles,0);assert.equal(rows.length,1);
 const firstNone=tacticalNoFirstMock();
 console.log(JSON.stringify({labels,defects,root1_wrapper:{begin,calls,handles,publicCPs:rows.length,first_completed_retained:true,receiver_reselection:false},firstNone,real_NN:0,model_load:0,browser:false}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
function tacticalNoFirstMock(){const result=vm.runInContext(`tacticalLabel(document.inputs[0],document.labels[0].certificate,{response:{classification:'first_none',causes:{initial_checkpoint_missing:true}}})`,context);assert.equal(result.label_verdict,null);return result;}
