'use strict';
function costCheckedState(input){
 const id=input.identity,prefix=structuredClone(id.legal_prefix);let state=fromPrefix([]);
 for(const action of prefix){if(!state.getLegalActions().some(a=>JSON.stringify(a)===JSON.stringify(action)))throw Error('COST_PREFIX_ILLEGAL');state=state.next(action);}
 if(state._positionKey()!==id.key||state.depth!==input.totalply||state.getCurrentPlayer()!==input.physical_side||terminalResult(state))throw Error('COST_INPUT_STATE');
 if(JSON.stringify([...state.position_history].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0))!==JSON.stringify(id.history))throw Error('COST_HISTORY');
 const f=state.toNNInput();const expected={features_bits:Array.from(new Uint32Array(f.buffer,f.byteOffset,f.length))};
 if(JSON.stringify(expected.features_bits)!==JSON.stringify(input.numeric.features_bits))throw Error('COST_FEATURES');
 return {state,prefix};
}
function costPreflight(document,input){
 if(document.issue!=='quoridor-4lc.137'||document.requests.length!==4||document.requests.map(x=>x.id).join(',')!=='warm,sample1,sample2,sample3'||document.engine!=='candidate'||document.physical_side!==1)throw Error('COST_PLAN');
 const {state,prefix}=costCheckedState(input);
 return {key:state._positionKey(),side:state.getCurrentPlayer(),totalply:state.depth,wall_remaining:[state.walls_p1,state.walls_p2],legal_prefix_plies:prefix.length,features648:true,history_map_exact:true,models_loaded:0,NN:0,actual_policy_both_slots:QUALITY_POLICY,classifier:browserRulesMock(),bounded_samples:2,fresh_tree_context_each_request:true};
}
async function runCostRequests(config,document,input){
 const attempts=document.requests.map(p=>({...p,status:'unstarted'}));
 for(const attempt of attempts){
  if(externalAbort||Date.now()>=Date.parse(config.processing_deadline))break;
  const wrapperBegin=epochMain(),zeroBegin=epochMain();await settlePlayerSearches();const zeroEnd=epochMain();
  const replayBegin=epochMain(),{state,prefix}=costCheckedState(input),replayEnd=epochMain();attempt.status='started';attempt.begin_ms=wrapperBegin;
  try{
   const {row}=await chooseBrowser({engine:document.engine,cancel:false,functional:true,numeric_selected:true,physical_side:input.physical_side,policy:QUALITY_POLICY,cost_sample:attempt.id,warm:attempt.warm},state,prefix,null,config);
   attempt.request_id=row.identity.request_id;attempt.public_classification=row.response.classification;
   const collectBegin=epochMain();await settlePlayerSearches();const zeroAfter=epochMain();await validateAfterProgression();const checked=epochMain();
   row.cost_spans={wrapper_start_ms:wrapperBegin,both_previous_zero_wait_start_ms:zeroBegin,both_previous_zero_wait_end_ms:zeroEnd,input_replay_start_ms:replayBegin,input_replay_end_ms:replayEnd,public_return_ms:collectBegin,both_zero_after_ms:zeroAfter,detail_validation_end_ms:checked};
   const numeric=row.diagnostic.numeric[0],a=[...numeric.policy_logits,numeric.value],b=[...input.numeric.policy_logits,input.numeric.value];
   if(JSON.stringify(numeric.features_bits)!==JSON.stringify(input.numeric.features_bits)||a.length!==137||a.some((x,i)=>Math.abs(x-b[i])>1e-4+1e-4*Math.abs(b[i])))throw Error('SAVED_ROOT_NUMERIC_MISMATCH');
   const series=row.diagnostic.sab_publications;if(series.some(p=>p.completed_backup!==p.loop_simulations+1||p.edge_sum!==p.loop_simulations))throw Error('ROOT_COUNT_CONVENTION');
   attempt.status=row.response.classification==='completed_legal'?'completed':'noncompleted';attempt.end_ms=epochMain();
  }catch(error){attempt.status='infra_or_numeric_failure';attempt.error={name:error.name,message:error.message};await settlePlayerSearches();break;}
 }
 return {...collectBrowser(),attempts,planned_requests:4,game_count:0,all_startup_separate:true,only_target_side_active:true};
}
