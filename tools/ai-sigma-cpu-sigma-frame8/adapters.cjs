'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'../..');
function replaceExactly(source,before,after,count=1) {
  const n=source.split(before).length-1;
  if(n!==count)throw Error('SOURCE_ADAPTER_COUNT '+before+' expected '+count+' got '+n);
  return source.split(before).join(after);
}
const paths={
  main:'tools/ai-sigma-player-workers/player-main.js',
  worker:'tools/ai-sigma-player-workers/player-worker.js',
  producer:'tools/ai-sigma-tail-transport/early-worker.js',
  checkpoint:'tools/ai-sigma-tail-transport/checkpoint.js',
  cache:'tools/ai-sigma-actual-boundary-repair/early-cache.cjs',
};
function script(name) {
  let source=fs.readFileSync(path.join(ROOT,paths[name]),'utf8');
  if(name==='main') {
    source=replaceExactly(source,'max_depth:spec.engine===\'reference\'?null:24,seed:1979','max_depth:spec.engine===\'reference\'?null:24,seed:config.seed');
    source=replaceExactly(source,'candidate_color:planned.candidate_color,seed:1979','candidate_color:planned.candidate_color,seed:config.seed');
    source=replaceExactly(source,'function gameFailureResult(classification, currentPlayer, engine) {','function gameFailureResult(classification, currentPlayer, engine, fault=null) {\n  if(classification===\'engine_fault\' && /IDENTITY|MODEL_BIND|PRODUCER_LIMITS/.test(fault?.error??\'\')) return {status:\'unfinished\',winner:null,reason:\'shared_identity_failure\',responsible_engine:engine,fault};\n  if(classification===\'engine_fault\' && engine===\'reference\' && /NN_BACKEND:|MODEL_|NN_FALLBACK|FALLBACK/.test(fault?.error??\'\')) return {status:\'unfinished\',winner:null,reason:\'reference_NN_invalid\',pair_invalid:true,responsible_engine:engine,fault};');
    source=replaceExactly(source,'gameFailureResult(failure,state.getCurrentPlayer(),engine)','gameFailureResult(failure,state.getCurrentPlayer(),engine,row.response.causes.received_fault)');
    source+='\n'+fs.readFileSync(__dirname+'/browser-glue.js','utf8');
  } else if(name==='worker') {
    source=replaceExactly(source,'const result = await originalInfer(bits);','let result;\n      try { result = await originalInfer(bits); }\n      catch(error) { if(![\'STALE_GENERATION\',\'guard\'].includes(error.message))error.message=\'NN_BACKEND:\'+error.message; throw error; }');
  } else if(name==='producer') {
    source=replaceExactly(source,'id.limits.seed!==1979','![1979,2098].includes(id.limits.seed)');
    source=replaceExactly(source,'generation,request_id:d.identity.request_id,simulations:','generation,seed:d.identity.limits.seed,request_id:d.identity.request_id,simulations:');
    source=replaceExactly(source,'seed:1979','seed:d.identity.limits.seed',2);
  } else if(name==='checkpoint') {
    source=replaceExactly(source,'generation:g,seed:1979','generation:g,seed:d.seed??1979');
    source=replaceExactly(source,'prefix:d.prefix??null,seed:1979','prefix:d.prefix??null,seed:req.seed');
  } else if(name==='cache') {
    source=replaceExactly(source,'prefix:this.identity.prefix,seed:1979','prefix:this.identity.prefix,seed:this.identity.limits.seed');
  }
  return source;
}
function bindings() {
  return Object.fromEntries(Object.entries(paths).map(([name,p])=>[name,{path:p,original_SHA256:crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,p))).digest('hex'),adapted_SHA256:crypto.createHash('sha256').update(script(name)).digest('hex')} ]));
}
module.exports={script,bindings};
