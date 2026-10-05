'use strict';
importScripts('/player-base.js');
importScripts('/deep-input.js');
const inheritedDeepHandler=onmessage;
let deepTraceEnabled=false,deepDeadline=null,deepRecords=[],deepNodes=[],deepNumeric=new WeakMap();
const inheritedDeepCheck=check;
check=function(context,beforeNewWork=false){
  if(deepDeadline && epoch()>=deepDeadline)throw Error('DEEP_COUNT_TIMEOUT');
  return inheritedDeepCheck(context,beforeNewWork);
};
function stateBinding(state){
  const features=state.toNNInput();
  return {key:state._positionKey(),history:[...state.position_history].sort((a,b)=>a[0].localeCompare(b[0])),ply:state.depth,turn:state.isPlayer1Turn()?0:1,features_bits:Array.from(new Uint32Array(features.buffer,features.byteOffset,features.length)),terminal:terminalResult(state),walls_remaining:[state.walls_p1,state.walls_p2]};
}
let deepEvaluatingNode=null;
const originalDeepExpand=expandNode;
expandNode=async function(node,evaluator){
  deepEvaluatingNode=node;
  try{return await originalDeepExpand(node,evaluator);}
  finally{deepEvaluatingNode=null;}
};
const originalDeepBackup=backup;
backup=function(node,value){
  const selected=deepTraceEnabled && deepNodes.length<8 && !deepNodes.includes(node);
  const path=[];let cursor=node;
  while(cursor.parent){cursor.ensureState();path.unshift(cursor);cursor=cursor.parent;}
  let record;
  if(selected){
    node.ensureState();deepNodes.push(node);
    record={...stateBinding(node.state),leaf_side_value:value,numeric:deepNumeric.get(node)??null,
      path_actions:path.map(x=>rustAction(x.parent.state,x.action)),
      pre_leaf:{visits:node.visitCount,valueSum:node.valueSum},
      pre_path:path.map(x=>({action:rustAction(x.parent.state,x.action),parent_visits:x.parent.visitCount,parent_valueSum:x.parent.valueSum,child_visits:x.visitCount,child_valueSum:x.valueSum,parentQ:x.parent.qValue,childQ:x.qValue}))};
  }
  originalDeepBackup(node,value);
  if(record){record.post_leaf={visits:node.visitCount,valueSum:node.valueSum};record.post_path=path.map(x=>({action:rustAction(x.parent.state,x.action),parent_visits:x.parent.visitCount,parent_valueSum:x.parent.valueSum,child_visits:x.visitCount,child_valueSum:x.valueSum,childQ:x.qValue}));deepRecords.push(record);}
};
let traceAbiPromise=null;
async function privateTraceAbi(){
  if(!traceAbiPromise)traceAbiPromise=(async()=>{
    const bytes=await(await fetch('/trace.wasm')).arrayBuffer(),e=(await WebAssembly.instantiate(bytes,{})).instance.exports,handles=new Set();
    function call(value){const input=new TextEncoder().encode(JSON.stringify(value)),h=e.ort_buffer(input.length);if(!h)throw Error('TRACE_BUFFER');new Uint8Array(e.memory.buffer,e.ort_ptr(h),input.length).set(input);let output;try{output=e.ort_call(h);const answer=JSON.parse(new TextDecoder().decode(new Uint8Array(e.memory.buffer,e.ort_ptr(output),e.ort_len(output))));if(!answer.ok)throw Error(answer.error);return answer.data;}finally{e.ort_free(h);if(output)e.ort_free(output);}}
    return {call,create:req=>{const h=call({op:'new',...req}).handle;handles.add(h);return h;},free:h=>{if(!handles.delete(h)||e.ort_free(h)!==1)throw Error('TRACE_HANDLE_FREE');},liveHandles:()=>handles.size};
  })();
  return traceAbiPromise;
}
async function deepSearch(data){
  if(data.engine!==boundEngine || active || activeNN || b.liveHandles())throw Error('DEEP_BINDING_OR_OLD_NOT_ZERO');
  const state=deepCheckedState(data.fixture),start=epoch();deepDeadline=start+data.timeout_ms;
  deepTraceEnabled=data.instrumented;deepRecords=[];deepNodes=[];deepNumeric=new WeakMap();
  const originals={call:b.call,create:b.create,free:b.free,liveHandles:b.liveHandles,infer:b.infer};
  let handle=null,cp=null,root=null,primary=null,firstCP=null,candidateTrace=null;
  const numeric=[],spans=[],candidateEvaluations=[];
  active=true;generation=data.generation;
  b.infer=async bits=>{
    if(epoch()>=deepDeadline)throw Error('DEEP_COUNT_TIMEOUT');
    activeNN++;const begin=epoch();
    try{const result=await originals.infer(bits);spans.push({wrapper_start_ms:begin,wrapper_end_ms:epoch(),API_start_ms:result.session_run_start_ms,API_end_ms:result.session_run_end_ms});if(!numeric.length)numeric.push({features_bits:Array.from(bits),policy_logits:result.logits,value:result.value});if(deepTraceEnabled&&deepEvaluatingNode)deepNumeric.set(deepEvaluatingNode,{features_bits:Array.from(bits),policy_logits:result.logits,value:result.value});return result;}finally{activeNN--;}
  };
  try{
    if(boundEngine==='candidate'){
      if(data.instrumented){const abi=await privateTraceAbi();b.call=abi.call;b.create=abi.create;b.free=abi.free;b.liveHandles=abi.liveHandles;}
      handle=b.create({prefix:deepRustPrefix(data.fixture.legal_prefix),diagnostic:true,simulations:data.K,max_nodes:512,max_depth:24,generation,seed:1979});
      while(true){
        if(epoch()>=deepDeadline)throw Error('DEEP_COUNT_TIMEOUT');
        const request=b.call({op:'begin',handle,generation});
        if(request.pending){
          const result=await b.infer(request.features_bits);
          if(data.instrumented && candidateEvaluations.length<8 && !candidateEvaluations.some(x=>x.key===request.key&&JSON.stringify(x.history)===JSON.stringify(request.history)))candidateEvaluations.push({...request,policy_logits:result.logits,value:result.value});
          b.call({op:'resume',handle,generation,token:request.token,logits:result.logits,value:result.value});
        }
        cp=b.call({op:'checkpoint',handle,generation});if(cp.action!==null&&firstCP===null)firstCP=epoch();
        if(cp.simulations===data.K)break;if(cp.simulations>data.K)throw Error('COUNT_EXCEEDS_K');await yieldTask();
      }
      cp=b.call({op:'snapshot',handle,generation});
      if(data.instrumented){candidateTrace=b.call({op:'trace',handle,generation}).nodes;for(const node of candidateTrace){node.numeric=candidateEvaluations.find(x=>x.key===node.key&&JSON.stringify([...x.history].sort((a,b)=>a[0].localeCompare(b[0])))===JSON.stringify([...node.history].sort((a,b)=>a[0].localeCompare(b[0]))))??null;node.final_node=cp.tree.find(x=>x.index===node.node_index);}}
    }else{
      const context={generation,cooperative:false,count_deadline:deepDeadline,nnCalls:0,simulations:0,spans:[],steps:[],onComplete:null};clockContext=context;
      root=await runMCTSControl(state,data.K-1,nnEvaluator,generation);firstCP=context.rootFinished??null;
      cp=referenceCP(root,{...context,nnCalls:spans.length},{generation});cp.tree=[];
      if(data.instrumented)deepRecords.forEach((record,i)=>{const node=deepNodes[i];record.final_node={visits:node.visitCount,valueSum:node.valueSum,parentQ:node.qValue,children:node.children.map(c=>({action:rustAction(node.state,c.action),visits:c.visitCount,valueSum:c.valueSum,childQ:c.qValue,basePrior:c.basePrior}))};});
    }
  }catch(error){primary={name:error.name,message:error.message,stack:error.stack};}
  finally{
    if(handle!==null)b.free(handle);
    const zero={handles:b.liveHandles(),activeNN,active:false};
    Object.assign(b,originals);clockContext=null;active=false;deepDeadline=null;
    const completed=boundEngine==='candidate'?(cp?.simulations??0):(root?.visitCount??0);
    send({kind:'deep_result',id:data.id,fixture_id:data.fixture.id,engine:boundEngine,instrumented:data.instrumented,generation,K:data.K,cp,numeric,spans,primary,zero,completed_backups:completed,NN_calls:spans.length,terminal_noNN_backups:completed-spans.length,first_CP_ms:firstCP,wrapper_start_ms:start,wrapper_end_ms:epoch(),trace:boundEngine==='candidate'?candidateTrace:deepRecords,candidate_parentQ_missing:boundEngine==='candidate'});
    deepTraceEnabled=false;
  }
}
onmessage=async event=>{
  if(event.data.kind!=='deep_search')return inheritedDeepHandler(event);
  try{await deepSearch(event.data);}catch(error){send({kind:'deep_result',id:event.data.id,primary:{name:error.name,message:error.message},zero:{handles:b?.liveHandles(),activeNN,active}});}
};
