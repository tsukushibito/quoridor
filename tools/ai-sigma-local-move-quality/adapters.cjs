'use strict';
const fs=require('fs'),crypto=require('crypto');
const base=require('../ai-sigma-diverse-prefix/adapters.cjs');
function replace(source,before,after,n=1){if(source.split(before).length-1!==n)throw Error('POLICY_ADAPTER_COUNT '+before);return source.split(before).join(after);}
function script(name){
 let source=base.script(name);
 if(name==='producer'){
  source=replace(source,"(id.engine==='candidate'?(id.limits.max_nodes!==512||id.limits.max_depth!==24):(id.limits.max_nodes!==null||id.limits.max_depth!==null))","(id.limits.max_nodes!==null||id.limits.max_depth!==null)");
  source=replace(source,"if(d.engine==='candidate'){const n=await b.numeric(d.fixture);","if(false){const n=await b.numeric(d.fixture);");
  source=replace(source,"if(d.identity.engine==='reference')await runReference(d,d.kind==='direct');else await run(d,d.kind==='direct');","await runReference(d,d.kind==='direct');");
  // This remains the original fixed Sigma kernel; candidate slot is only physical-player identity.
  source=replace(source,"if(d.identity.engine==='reference'){const terminal=","if(true){const terminal=");
  source=replace(source,"compile_ms:b.compile_ms,handles:","compile_ms:b.compile_ms,policy:'fixedSigma C1/FPU.2/first/temp0/originalorder',physical_slot:d.engine,handles:");
 }else if(name==='cache'){
  source=replace(source,"const ref=this.identity.engine==='reference';","const ref=true; // Both transport slots are fixedSigma in134.");
 }else if(name==='worker'){
  source=replace(source,'validation_end_ms: workerNow()','validation_end_ms: workerNow(), policy: \'fixedSigma\', cp_NN_calls: cp.nn_calls, completed_backup: cp.root_visits, rootN: cp.root_visits, loop_simulations: cp.simulations, edge_sum: cp.root_edges.reduce((sum,e)=>sum+e[2],0)');
 }else if(name==='main'){
  source=replace(source,"simulations:spec.engine==='reference'?100000:4096,max_nodes:spec.engine==='reference'?null:512,max_depth:spec.engine==='reference'?null:24","simulations:100000,max_nodes:null,max_depth:null");
  source=replace(source,'BrowserNumeric.check({engine,state:referenceState(fixture)','BrowserNumeric.check({engine:\'reference\',state:referenceState(fixture)');
  source=replace(source,'public_did_not_await_ACK:true,Node_clock_referee_calls:0','adopt_checkpoint:checkpoint?{sequence:checkpoint.sequence,action:checkpoint.action,visits:checkpoint.visits,value:checkpoint.value}:null,public_did_not_await_ACK:true,Node_clock_referee_calls:0');
  source=replace(source,"engine==='reference' && /NN_BACKEND:","/NN_BACKEND:");
  source=replace(source,"row.gate=BrowserNumeric.check({engine:row.spec.engine,state,numeric:diagnostic.numeric[0],cp:diagnostic.validated_cp,reference});","row.gate=row.spec.numeric_selected?BrowserNumeric.check({engine:'reference',state,numeric:diagnostic.numeric[0],cp:diagnostic.validated_cp,reference}):{selected:false,missing_not_zero:true};\n    row.adopted_stats=diagnostic.sab_publications.find(p=>p.sequence===row.response.body.sequence)??null;");
  source=replace(source,"if(!diagnostic?.numeric?.length)throw Error('ROOT_NUMERIC_MISSING');","if(!diagnostic?.numeric?.length && row.spec.numeric_selected && row.response.classification==='completed_legal')throw Error('ROOT_NUMERIC_MISSING');");
  source+='\n'+fs.readFileSync(__dirname+'/../ai-sigma-deep-node-comparison/deep-input.js','utf8');
  source+='\n'+fs.readFileSync(__dirname+'/quality-main.js','utf8');
 }
 return source;
}
function bindings(){return Object.fromEntries(Object.entries(base.bindings()).map(([name,v])=>[name,{...v,adapted_SHA256:crypto.createHash('sha256').update(script(name)).digest('hex'),policy134:'both slots fixedSigma; independent transport binding'}]));}
module.exports={script,bindings};
