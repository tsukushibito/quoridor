'use strict';
importScripts('/player-base.js');importScripts('/deep-input.js');
const inheritedMeanHandler=onmessage;
const meanABIs=new Map();
async function meanABI(variant){
 if(!['q0','fpu'].includes(variant))throw Error('VARIANT_SCHEMA');
 if(!meanABIs.has(variant))meanABIs.set(variant,(async()=>{
  const bytes=await(await fetch('/'+variant+'.wasm')).arrayBuffer(),e=(await WebAssembly.instantiate(bytes,{})).instance.exports,handles=new Set();
  function call(value){const input=new TextEncoder().encode(JSON.stringify(value)),h=e.ort_buffer(input.length);if(!h)throw Error('MEAN_BUFFER');new Uint8Array(e.memory.buffer,e.ort_ptr(h),input.length).set(input);let o;try{o=e.ort_call(h);const answer=JSON.parse(new TextDecoder().decode(new Uint8Array(e.memory.buffer,e.ort_ptr(o),e.ort_len(o))));if(!answer.ok)throw Error(answer.error);return answer.data;}finally{e.ort_free(h);if(o)e.ort_free(o);}}
  return {call,create:req=>{const h=call({op:'new',...req}).handle;handles.add(h);return h;},free:h=>{if(!handles.delete(h)||e.ort_free(h)!==1)throw Error('MEAN_FREE');},liveHandles:()=>handles.size};
 })());return meanABIs.get(variant);
}
async function meanSearch(d){
 if(boundEngine!=='candidate'||d.engine!=='candidate'||active||activeNN||b.liveHandles()||!['original','q0','fpu'].includes(d.variant))throw Error('MEAN_BINDING_OLD_ZERO');
 const prepareStart=epoch(),state=deepCheckedState(d.fixture),start=epoch(),deadline=start+d.timeout_ms;
 const originals={call:b.call,create:b.create,free:b.free,liveHandles:b.liveHandles,infer:b.infer};
 let handle=null,cp=null,primary=null,firstCP=null,trace=null;const spans=[],numeric=[],CPs=[],evaluations=[];
 active=true;generation=d.generation;
 b.infer=async bits=>{if(epoch()>=deadline)throw Error('COUNT_TIMEOUT');activeNN++;const begin=epoch();try{const result=await originals.infer(bits);spans.push({wrapper_start_ms:begin,wrapper_end_ms:epoch(),API_start_ms:result.session_run_start_ms,API_end_ms:result.session_run_end_ms});return result;}finally{activeNN--;}};
 try{
  if(d.variant!=='original'){const abi=await meanABI(d.variant);Object.assign(b,{call:abi.call,create:abi.create,free:abi.free,liveHandles:abi.liveHandles});}
  handle=b.create({prefix:deepRustPrefix(d.fixture.legal_prefix),diagnostic:true,simulations:d.K,max_nodes:512,max_depth:24,generation,seed:1979});
  while(true){
   if(epoch()>=deadline)throw Error('COUNT_TIMEOUT');const request=b.call({op:'begin',handle,generation});
   if(request.pending){const result=await b.infer(request.features_bits),rec={...request,policy_logits:result.logits,value:result.value};if(!numeric.length)numeric.push(rec);if(evaluations.length<8&&!evaluations.some(x=>x.key===request.key&&JSON.stringify(x.history)===JSON.stringify(request.history)))evaluations.push(rec);b.call({op:'resume',handle,generation,token:request.token,logits:result.logits,value:result.value});}
   cp=b.call({op:'checkpoint',handle,generation});CPs.push({epoch_ms:epoch(),cp});if(cp.action!==null&&firstCP===null)firstCP=epoch();
   if(cp.simulations===d.K)break;if(cp.simulations>d.K)throw Error('COUNT_EXCEEDS_K');await yieldTask();
  }
  cp=b.call({op:'snapshot',handle,generation});
  if(d.variant!=='original'){trace=b.call({op:'mean_trace',handle,generation});if(trace.FPU_enabled!==(d.variant==='fpu'))throw Error('FPU_FLAG_MIXED');for(const n of trace.nodes)n.numeric=evaluations.find(x=>x.key===n.key&&JSON.stringify(x.history)===JSON.stringify(n.history))??null;}
 }catch(e){primary={name:e.name,message:e.message,stack:e.stack};}
 finally{
  const stopStart=epoch();if(handle!==null)b.free(handle);const zero={handles:b.liveHandles(),activeNN,active:false};Object.assign(b,originals);active=false;
  send({kind:'mean_result',id:d.id,fixture_id:d.fixture.id,engine:boundEngine,variant:d.variant,generation,K:d.K,cp,numeric,spans,CPs,trace,primary,zero,completed_backups:cp?.simulations??0,NN_calls:spans.length,terminal_noNN_backups:(cp?.simulations??0)-spans.length,first_CP_ms:firstCP,prepare_start_ms:prepareStart,wrapper_start_ms:start,stop_start_ms:stopStart,wrapper_end_ms:epoch()});
 }
}
onmessage=async event=>{if(event.data.kind!=='mean_search')return inheritedMeanHandler(event);try{await meanSearch(event.data);}catch(e){send({kind:'mean_result',id:event.data.id,fixture_id:event.data.fixture?.id,variant:event.data.variant,primary:{name:e.name,message:e.message,stack:e.stack},zero:{handles:b?.liveHandles(),activeNN,active}});}};
