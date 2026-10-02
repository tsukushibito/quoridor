importScripts('/sab-adapter.js');
const inheritedHandler=onmessage;
onmessage=async function(event) {
  const data=event.data;
  if(data.kind!=='count_search')return inheritedHandler(event);
  if(active||activeNN||b.liveHandles())throw Error('COUNT_OWNERSHIP_OVERLAP');
  let handle=null,primary=null,cp=null;
  const start=epoch(),numeric=[],spans=[],backupCounts=[];
  active=true;
  try {
    handle=b.create({fixture:data.fixture,diagnostic:true,simulations:data.K,max_nodes:512,max_depth:24,generation:data.generation,seed:1979});
    while(true) {
      if(epoch()-start>=data.timeout_ms)throw Error('COUNT_SEARCH_TIMEOUT');
      const begin=epoch(),request=b.call({op:'begin',handle,generation:data.generation});
      if(request.pending) {
        activeNN++;let result;
        const wrapperStart=epoch();
        try {result=await b.infer(request.features_bits);}finally{activeNN--;}
        spans.push({wrapper_start_ms:wrapperStart,wrapper_end_ms:epoch(),API_start_ms:result.session_run_start_ms,API_end_ms:result.session_run_end_ms});
        if(!numeric.length)numeric.push({features_bits:request.features_bits,policy_logits:result.logits,value:result.value});
        b.call({op:'resume',handle,generation:data.generation,token:request.token,logits:result.logits,value:result.value});
      }
      cp=b.call({op:'checkpoint',handle,generation:data.generation});
      backupCounts.push({simulations:cp.simulations,NN:spans.length,step_ms:epoch()-begin});
      if(cp.simulations===data.K)break;
      if(cp.simulations>data.K)throw Error('COUNT_EXCEEDS_K');
      await yieldTask();
    }
    cp=b.call({op:'snapshot',handle,generation:data.generation});
  }catch(error){primary={name:error.name,message:error.message};}
  finally {
    if(handle!==null){b.free(handle);handle=null;}
    active=false;
    nativePostMessage({kind:'count_result',id:data.id,fixture_id:data.fixture.id,K:data.K,cp,numeric,spans,backup_counts:backupCounts,primary,wrapper_start_ms:start,wrapper_end_ms:epoch(),zero:{handles:b.liveHandles(),activeNN,active},NN_calls:spans.length,noNN_backups:(cp?.simulations??0)-spans.length});
  }
};
