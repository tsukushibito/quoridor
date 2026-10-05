'use strict';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const identityKeys=['request_id','generation','prefix','legal_prefix','seed','simulations','max_nodes','max_depth','T_ms','g_ms'];
function validate(response,req,judge){
 const envelope=response.raw?.payload,body=response.engine==='reference'?envelope:envelope?.payload;
 const data=response.engine==='reference'?body:body?.data,cp=response.engine==='reference'?null:data?.checkpoint;
 if(response.transaction_bound!==true||!['candidate','reference'].includes(response.engine)||identityKeys.some(k=>!same(envelope?.transaction?.[k],req[k]))||envelope?.transaction?.engine!==response.engine)return 'IDENTITY_MISMATCH';
 if(envelope.generation!==req.generation||response.generation!==req.generation||response.request_id!==req.request_id)return 'IDENTITY_MISMATCH';
 if(response.error)return response.error;
 if(!Number.isInteger(response.fallback)||response.fallback!==0)return 'NN_FALLBACK';
 if(typeof response.owned_binding!=='boolean'||response.owned_binding!==true)return 'OWNED_IDENTITY_MISMATCH';
 const terminal=judge.terminalResult(judge.state(req.legal_prefix));
 if(terminal){if(response.action!==null||response.nn_calls!==0||!same(response.terminal,terminal))return 'TERMINAL_SHAPE';}
 else{if(!Number.isInteger(response.action)||response.action<0||response.action>208)return 'ACTION_SHAPE';judge.validate(req.legal_prefix,response.action);}
 if(!Number.isInteger(response.nn_calls)||response.nn_calls<0)return 'NN_CALLS_SHAPE';
 if(cp){const {spans,...base}=cp;if(!same(base,data.owned?.cp)||!same(data.original_checkpoint,data.owned?.cp))return 'OWNED_CHECKPOINT_MISMATCH';
  if(cp.policy_fallbacks!==0||cp.value_fallbacks!==0||!Number.isInteger(cp.simulations)||cp.simulations<0||cp.simulations>req.simulations)return 'CHECKPOINT_SHAPE';
  if(!Array.isArray(cp.root_edges)||cp.root_edges.some(e=>!Array.isArray(e)||e.length!==4||e.some(x=>!Number.isFinite(x))||!Number.isInteger(e[0])||e[0]<0||e[0]>208||e[1]<0||!Number.isInteger(e[2])||e[2]<0||Math.abs(e[3])>e[2]+1e-4*Math.max(1,e[2])))return 'CHECKPOINT_FINITE';
  if(!terminal&&(cp.root_edges.length===0||Math.abs(cp.root_edges.reduce((s,e)=>s+e[1],0)-1)>1e-5))return 'PRIOR_NORMALIZATION';
 }
 if(response.accepted!==true||response.checkpoint!==true||response.legal!==true||response.illegal!==false||response.stale!==false)return 'DELIVERY_GATE';
 return null;
}
function finalize(response,req,judge,clock){
 let error=response.error??null;try{if(!error)error=validate(response,req,judge);}catch(e){error=e.message==='IDENTITY_MISMATCH'?e.message:'REFEREE_ERROR';response.validation_error=e.message;}
 if(error){response.error=error;response.accepted=false;}else response.accepted=true;
 // Required response encoding and full legality/type validation precede the final caller stamp.
 JSON.stringify(response);const stamp=clock();response.received_after_validation_ms=stamp;response.elapsed_ms=stamp-response.t0_ms;response.late=stamp>=response.t0_ms+response.T_ms;response.overshoot_ms=Math.max(0,response.elapsed_ms-response.T_ms);
 if(response.late){response.error=response.error??'LATE_RESPONSE';response.accepted=false;}
 response.accepted=response.accepted===true;
 if(!response.accepted){response.rejected_action=response.action??null;response.action=null;response.checkpoint=false;}
 response.final_validation_and_serialization_before_stamp=true;
 return response;
}
module.exports={validate,finalize};
