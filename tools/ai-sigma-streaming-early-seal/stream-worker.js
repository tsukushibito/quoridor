importScripts('/ort/ort.min.js','/candidate-host.js','/checkpoint.js','/game.js','/context.js');
let b,generation=0,active=false;const epoch=()=>performance.timeOrigin+performance.now(),yieldTask=()=>new Promise(r=>setTimeout(r,0));
const busy=ms=>{const end=epoch()+ms;while(epoch()<end){}};
async function request(d){if(active)throw Error('OVERLAPPING_REQUEST');const state=d.identity.fixture?referenceState(d.identity.fixture):fromPrefix(d.identity.legal_prefix),h=Array.from(state.position_history).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);let replay=fromPrefix([]),ids=[];for(const a of d.identity.legal_prefix??[]){ids.push(rustAction(replay,a));replay=replay.next(a)}if(!d.identity.fixture&&JSON.stringify(ids)!==JSON.stringify(d.identity.prefix)||state._positionKey()!==d.identity.key||JSON.stringify(h)!==JSON.stringify(d.identity.history)||d.identity.model!==b.digest||d.identity.schema!=='8x9x9-f32/136logits/value1/rust209'||d.identity.epoch!==d.identity.generation)throw Error('PRODUCER_CONTEXT_IDENTITY');active=true;generation=d.identity.generation;let seq=0;const nn=[],numeric=[];const infer=b.infer;b.infer=async bits=>{const start=epoch();postMessage({kind:'nn_start',identity:d.identity,start_ms:start,nn_index:nn.length+1});if(d.before_first_nn_busy_ms&&nn.length===0)busy(d.before_first_nn_busy_ms);const r=await infer(bits);const end=epoch();nn.push({start_ms:start,end_ms:end,actual_nn_ms:r.nn_ms});if(!numeric.length)numeric.push({features_bits:Array.from(bits),policy_logits:r.logits,value:r.value});postMessage({kind:'nn_end',identity:d.identity,...nn.at(-1)});return r;};
 try{const r=await runOwned({fixture:d.identity.fixture??undefined,prefix:d.identity.prefix??undefined,generation,request_id:d.identity.request_id,simulations:d.identity.limits.simulations,max_nodes:512,max_depth:24,capture_tree:!!d.capture_tree,capture_trace:!!d.capture_tree},{b,epoch,yieldTask,getGeneration:()=>generation,completed:o=>{
   const message={kind:'snapshot',identity:d.identity,sequence:++seq,owned:o,sent_ms:epoch()};
   if(d.notification_injection==='foreign-prefix'&&seq===1){postMessage({...message,identity:{...d.identity,prefix:[999]}});}
   if(d.notification_injection==='nonfinite'&&seq===1){const bad=structuredClone(message);bad.owned.cp.root_edges[0][1]=NaN;postMessage(bad);}
   if(d.notification_injection==='duplicate'&&seq===2){postMessage({...message,sequence:1});}
   const send=()=>postMessage(message);if(d.notify_delay_ms)setTimeout(send,d.notify_delay_ms);else send();
   if(d.hardfault_after_cp===seq){postMessage({kind:'fault',identity:d.identity,error:'INJECTED_HARDFAULT',sent_ms:epoch()});throw Error('INJECTED_HARDFAULT');}
   if(d.nonyield_after_cp===seq)busy(d.nonyield_ms);
  }});
  if(r.error)postMessage({kind:'fault',identity:d.identity,error:r.error,sent_ms:epoch()});
  postMessage({kind:'done',identity:d.identity,result:r,nn,numeric,worker_done_ms:epoch()});
 }catch(e){postMessage({kind:'fault',identity:d.identity,error:e.message,sent_ms:epoch()});}finally{b.infer=infer;active=false;postMessage({kind:'request_stopped',identity:d.identity,worker_stopped_ms:epoch(),NN:nn});}}
onmessage=async({data:d})=>{if(d.kind==='cancel'){generation=d.generation;postMessage({kind:'cancel_ack',generation,at_ms:epoch()});return;}
 try{if(d.kind==='load'){b=await loadOrtHost();generation=1;const warm=await runOwned({prefix:[],generation,request_id:'startup-warm',simulations:1},{b,epoch,yieldTask,getGeneration:()=>generation});if(warm.error)throw Error('WARM_'+warm.error);postMessage({kind:'ready',digest:b.digest,threads:b.threads,proxy:b.proxy,load_ms:b.load_ms,compile_ms:b.compile_ms,warm_NN:warm.calls,memory:b.e.memory.buffer.byteLength});}
 else if(d.kind==='request')await request(d);
 else if(d.kind==='direct'){generation=d.generation;const r=await runOwned({prefix:d.prefix,generation,request_id:d.request_id,simulations:8,capture_tree:true,capture_trace:true},{b,epoch,yieldTask,getGeneration:()=>generation});postMessage({kind:'direct',result:r});}
 }catch(e){postMessage(d.kind==='request'&&d.identity?{kind:'fault',identity:d.identity,error:e.message,sent_ms:epoch()}:{kind:'failed',error:e.message});}};
