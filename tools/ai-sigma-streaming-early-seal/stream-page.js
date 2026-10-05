const epoch=()=>performance.timeOrigin+performance.now();let worker,readyResolve,directResolve,current=null,ready,rawMessages=[];
function history(s){return Array.from(s.position_history).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0)}
function rustPrefix(prefix){let s=fromPrefix([]),out=[];for(const a of prefix){out.push(rustAction(s,a));s=s.next(a)}return out}
async function loadStream(){ready=new Promise(r=>readyResolve=r);worker=new Worker('/stream-worker.js');worker.onmessage=({data:m})=>{
 rawMessages.push({...m,caller_received_ms:epoch()});
 if(m.kind==='ready'||m.kind==='failed')readyResolve(m);
 else if(m.kind==='direct')directResolve(m);
 else if(current&&m.identity?.request_id===current.identity.request_id){
  if(['snapshot','fault','cancel'].includes(m.kind)){current.cache.receive(m);if(m.kind==='snapshot'&&current.spec.busy_on_first_snapshot&&!current.busy){current.busy=true;const end=epoch()+current.spec.busy_on_first_snapshot;while(epoch()<end){}}}
  if(m.kind==='done'){current.done=m;if(current.spec.fixed_amount)current.finish('fixed_amount');}
  if(m.kind==='request_stopped'){current.stopped=m;current.stopResolve?.(m);}
 }
};worker.onerror=e=>{if(current)current.cache.receive({kind:'fault',identity:current.identity,error:'WORKER_HARDFAULT',at_ms:epoch()});else readyResolve({kind:'failed',error:e.message})};worker.postMessage({kind:'load'});return await ready;}
function directGolden(f,generation){return new Promise(resolve=>{directResolve=resolve;worker.postMessage({kind:'direct',prefix:rustPrefix(f.legal_prefix),generation,request_id:'direct-'+f.id})})}
async function streamRequest(spec,f){
 const t0=spec.caller_t0_ms??epoch(); // immutable input available; prefix/context conversion below is charged
 const artificial=f.classification!=='legal-replay',state=artificial?referenceState(f):fromPrefix(f.legal_prefix),terminal=terminalResult(state),prefix=artificial?null:rustPrefix(f.legal_prefix);
 const identity={request_id:spec.request_id,generation:spec.generation,epoch:spec.generation,legal_prefix:artificial?null:f.legal_prefix,fixture:artificial?f:null,prefix,key:state._positionKey(),history:history(state),model:'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d',schema:'8x9x9-f32/136logits/value1/rust209',limits:{simulations:spec.fixed_amount?8:4096,max_nodes:512,max_depth:24,seed:1979},t0_ms:t0,deadline_ms:t0+spec.T_ms};
 const expected={legal:terminal?[]:state.getLegalActions().map(a=>rustAction(state,a)),terminal};
 const cache=new SnapshotCache(identity,expected,epoch),local={identity,cache,spec,busy:false};current=local;
 const result=await new Promise(resolve=>{
  let timer,cancelTimer;local.finish=reason=>{if(cache.sealed)return;clearTimeout(timer);clearTimeout(cancelTimer);const sealed=cache.seal(reason),beforeEncode=epoch(),encoded=JSON.stringify(sealed);const delivered=epoch();
   // Invalidation is local/immediate. Stopping inference is a distinct asynchronous action.
   worker.postMessage({kind:'cancel',generation:identity.generation+1});local.invalidated_ms=epoch();
   resolve({sealed,identity,caller_delivery_ms:delivered,caller_elapsed_ms:delivered-t0,caller_late:delivered>=identity.deadline_ms,overshoot_ms:Math.max(0,delivered-identity.deadline_ms),encoding_ms:delivered-beforeEncode,serialized_bytes:new TextEncoder().encode(encoded).length,cache_events:cache.events,cache_snapshots:rawMessages.filter(m=>m.kind==='snapshot'&&m.identity?.request_id===identity.request_id)});
  };
  const wake=()=>{if(epoch()<identity.deadline_ms){timer=setTimeout(wake,Math.max(0,identity.deadline_ms-epoch()));return}local.finish('deadline')};timer=setTimeout(wake,Math.max(0,identity.deadline_ms-epoch()));
  if(spec.cancel_after_ms!=null)cancelTimer=setTimeout(()=>{cache.receive({kind:'cancel',identity,error:'CANCELLED'});local.finish('cancel')},spec.cancel_after_ms);
  worker.postMessage({...spec,kind:'request',identity,capture_tree:!!spec.fixed_amount});
 });
 local.delivered=result;return result;
}
async function collectObservation(){const local=current,result=local.delivered,identity=local.identity,spec=local.spec,cache=local.cache;
 // Observation is outside the delivered move clock. No next NN starts until full owned cleanup.
 await Promise.race([local.stopped?Promise.resolve():new Promise(r=>local.stopResolve=r),new Promise(r=>setTimeout(r,400))]);
 const observed_ms=epoch(),messages=rawMessages.filter(m=>m.identity?.request_id===identity.request_id);
 const original=JSON.stringify(result.sealed);cache.receive({kind:'fault',identity,error:'AFTER_SEAL_INJECTED_FAULT'});const unchanged=original===JSON.stringify(cache.seal());
 return {cache_events:cache.events,postseal_unchanged:unchanged,all_messages:messages,worker_stopped:local.stopped??null,observation_end_ms:observed_ms,continued_after_seal_ms:Math.max(0,(local.stopped?.worker_stopped_ms??observed_ms)-result.sealed.decision_ms),NN_spans:messages.filter(m=>m.kind==='nn_end'),actual_NN_crossings:messages.filter(m=>m.kind==='nn_end'&&m.start_ms<identity.deadline_ms&&m.end_ms>=identity.deadline_ms&&!spec.before_first_nn_busy_ms).length,artificial_nonyield:!!(spec.nonyield_ms||spec.before_first_nn_busy_ms)};
}

function stopStreamWorker(){if(worker){worker.terminate();worker=null;}return {terminated_ms:epoch(),forced:true,worker_termination_API_has_no_wait_ack:true};}
