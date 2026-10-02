'use strict';
let unvisitedMode='original';
let fpuSelections=[];
importScripts('/player-base.js');
const countInheritedHandler=onmessage;
const countOriginalCheck=check;
check=function(context,beforeNewWork=false){
  if(context?.count_deadline && epoch()>=context.count_deadline)throw Error('COUNT_SEARCH_TIMEOUT');
  return countOriginalCheck(context,beforeNewWork);
};

async function countSearch(data){
  if(data.engine!==boundEngine || (boundEngine==='candidate'?data.condition!=='A':!['B','C'].includes(data.condition)))throw Error('COUNT_CONDITION_BINDING');
  if(active || activeNN || b.liveHandles() || unvisitedMode!=='original')throw Error('COUNT_OLD_NOT_ZERO_OR_FLAG_LEAK');
  const start=epoch();
  const deadline=start+data.timeout_ms;
  let handle=null,cp=null,root=null,primary=null,firstCP=null;
  const numeric=[],spans=[],backupCounts=[];
  const originalInfer=b.infer;
  active=true;generation=data.generation;fpuSelections=[];
  unvisitedMode=data.condition==='C'?'Q0':'original';
  b.infer=async function(bits){
    if(epoch()>=deadline)throw Error('COUNT_SEARCH_TIMEOUT');
    activeNN++;
    const begin=epoch();
    try{
      const result=await originalInfer(bits);
      spans.push({wrapper_start_ms:begin,wrapper_end_ms:epoch(),API_start_ms:result.session_run_start_ms,API_end_ms:result.session_run_end_ms});
      if(!numeric.length)numeric.push({features_bits:Array.from(bits),policy_logits:result.logits,value:result.value});
      if(epoch()>=deadline)throw Error('COUNT_SEARCH_TIMEOUT');
      return result;
    }finally{activeNN--;}
  };
  try{
    if(data.condition==='A'){
      handle=b.create({fixture:data.fixture,diagnostic:true,simulations:data.K,max_nodes:512,max_depth:24,generation,seed:1979});
      while(true){
        if(epoch()>=deadline)throw Error('COUNT_SEARCH_TIMEOUT');
        const request=b.call({op:'begin',handle,generation});
        if(request.pending){
          const result=await b.infer(request.features_bits);
          b.call({op:'resume',handle,generation,token:request.token,logits:result.logits,value:result.value});
        }
        cp=b.call({op:'checkpoint',handle,generation});
        if(cp.action!==null && firstCP===null)firstCP=epoch();
        backupCounts.push({completed_backups:cp.simulations,NN_calls:spans.length,at_ms:epoch()});
        if(cp.simulations===data.K)break;
        if(cp.simulations>data.K)throw Error('COUNT_EXCEEDS_K');
        await yieldTask();
      }
      cp=b.call({op:'snapshot',handle,generation});
    }else{
      const state=referenceState(data.fixture);
      const context={generation,cooperative:false,count_deadline:deadline,nnCalls:0,simulations:0,spans:[],steps:[],onComplete:null};
      clockContext=context;
      root=await runMCTSControl(state,data.K-1,nnEvaluator,generation);
      firstCP=context.rootFinished??null;
      cp=referenceCP(root,{...context,nnCalls:spans.length},{generation});
      cp.tree=[];
      backupCounts.push({completed_backups:root.visitCount,loop_backups:context.simulations,NN_calls:spans.length,at_ms:epoch()});
    }
  }catch(error){primary={name:error.name,message:error.message,stack:error.stack};}
  finally{
    if(handle!==null)b.free(handle);
    clockContext=null;b.infer=originalInfer;active=false;
    const usedMode=unvisitedMode;unvisitedMode='original';
    const completed=data.condition==='A'?(cp?.simulations??0):(root?.visitCount??0);
    const rootNode=root?{truevisitCount:root.visitCount,valueSum:root.valueSum,parentQ:root.qValue,visitedChildBasePriorSum:root.children.filter(x=>x.visitCount>0).reduce((s,x)=>s+x.basePrior,0),children:root.children.map(x=>({action:rustAction(root.state,x.action),basePrior:x.basePrior,visitCount:x.visitCount,valueSum:x.valueSum,childQ:x.qValue}))}:null;
    send({kind:'count_result',id:data.id,condition:data.condition,fixture_id:data.fixture.id,generation,K:data.K,cp,numeric,spans,backup_counts:backupCounts,primary,wrapper_start_ms:start,wrapper_end_ms:epoch(),first_CP_ms:firstCP,zero:{handles:b.liveHandles(),activeNN,active,mode:unvisitedMode},used_mode:usedMode,NN_calls:spans.length,completed_backups:completed,terminal_noNN_backups:completed-spans.length,root_node:rootNode,root_FPU_selections:fpuSelections,candidate_parentQ_missing:data.condition==='A'});
  }
}
onmessage=async function(event){
  if(event.data.kind!=='count_search')return countInheritedHandler(event);
  try{await countSearch(event.data);}catch(error){send({kind:'count_result',id:event.data.id,condition:event.data.condition,fixture_id:event.data.fixture.id,primary:{name:error.name,message:error.message},zero:{handles:b?.liveHandles()??null,activeNN,active,mode:unvisitedMode}});}
};
