'use strict';
const fs=require('fs'),crypto=require('crypto'),base=require('../ai-sigma-local-move-quality/adapters.cjs');
function replace(s,a,b,n=1){if(s.split(a).length-1!==n)throw Error('COST_ADAPTER_COUNT '+a);return s.split(a).join(b);}
function script(name){let s=base.script(name);
 if(name==='main'){
  s=replace(s,'const stopPromise=waitingMessage(\'stop-\'+requestId);',"const inputPrepareEnd=epochMain();let dispatch_ms=null;const stopPromise=waitingMessage('stop-'+requestId);");
  s=replace(s,"explorationWorker.postMessage({kind:'request',identity,shared:memory", "dispatch_ms=epochMain();explorationWorker.postMessage({kind:'request',identity,shared:memory");
  s=replace(s,'const row={spec,identity,response,stop:null',"const row={spec,identity,response,cost_markers:{input_prepare_start_ms:t0,input_prepare_end_ms:inputPrepareEnd,dispatch_ms},stop:null");
  s+='\n'+fs.readFileSync(__dirname+'/cost-main.js','utf8');
 }else if(name==='worker'){
  s=replace(s,'let NNcontrolEvents = [];','let NNcontrolEvents = [];let costWorkerMarkers=[];');
  s=replace(s,"if (data.kind === 'request') {\n    if (active", "if (data.kind === 'request') {\n    costWorkerMarkers=[{kind:'worker_request_enter',at_ms:workerNow()}];\n    if (active");
  s=replace(s,'latestCP = null; publications = []; NNcontrolEvents = []; discardedSnapshots = 0;',"latestCP = null; publications = []; NNcontrolEvents = []; discardedSnapshots = 0;costWorkerMarkers.push({kind:'worker_input_control_cache_ready',at_ms:workerNow()});");
  s=replace(s,'sab_publications: publications, validation_events:', 'cost_worker_markers:costWorkerMarkers, sab_publications: publications, validation_events:');
  // Capture only root statistics after the original atomic publication path returns.
  s=replace(s,"edge_sum: cp.root_edges.reduce((sum,e)=>sum+e[2],0)","edge_sum: cp.root_edges.reduce((sum,e)=>sum+e[2],0), root_edges:cp.root_edges.map(e=>e.slice()), terminal_value:cp.terminal_value, readonly_copy_end_ms:workerNow()");
 }else if(name==='producer'){
  s=replace(s,'result={error:e.message,calls:c.nnCalls,completed_NN:nn.length,live_searches:0};', 'result={error:e.message,calls:c.nnCalls,completed_NN:nn.length,live_searches:0,spans:c.spans,steps:c.steps,rootFinished:c.rootFinished??null};');
 }
 return s;
}
function bindings(){return Object.fromEntries(Object.entries(base.bindings()).map(([n,v])=>[n,{...v,adapted_SHA256:crypto.createHash('sha256').update(script(n)).digest('hex'),policy137:'both fixedSigma, root CP readonly capture after original publication; original CP selection unchanged'}]));}
module.exports={script,bindings};
