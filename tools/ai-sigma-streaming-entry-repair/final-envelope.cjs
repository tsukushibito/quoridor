'use strict';const J=require('./judge.cjs');
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function finalize(r,id,clock,control={}){
 let body={...r,engine:id.engine,request_id:id.request_id,generation:id.generation,epoch:id.epoch,t0_ms:id.t0_ms,T_ms:500};
 if(r.engine!==undefined&&r.engine!==id.engine||!r.local_timeout&&!eq(r.echo,id))body={...body,accepted:false,error:'FINAL_IDENTITY'};
 for(const k of ['engine','request_id','generation','epoch','model','schema','limits','fixture_id'])if(r[k]!==undefined&&!eq(r[k],id[k]))body={...body,accepted:false,error:'FINAL_IDENTITY'};
 if(r.prefix_sha256!==undefined&&r.prefix_sha256!==J.hash(id.legal_prefix)||r.history_sha256!==undefined&&r.history_sha256!==J.hash(id.history))body={...body,accepted:false,error:'FINAL_IDENTITY'};
 if(typeof body.accepted!=='boolean'||typeof body.checkpoint!=='boolean')body={...body,accepted:false,error:'FINAL_IDENTITY'};
 if(body.accepted){try{if(!body.checkpoint||body.partial||body.fallback>0)throw Error(body.fallback>0?'NN_FALLBACK':'no_checkpoint');if(!Number.isFinite(body.value)||Math.abs(body.value)>1)throw Error('STRICT_VALUE');if(body.action!==null)J.validate(id.legal_prefix,body.action);else if(!J.terminalResult(J.state(id.legal_prefix)))throw Error('FINAL_LEGAL');}catch(e){body={...body,accepted:false,error:e.message};}}
 if(!body.accepted)body={...body,action:null,checkpoint:false,value:null};
 if(control.beforeFinalStamp)control.beforeFinalStamp({response:body,clock});
 let public_json=JSON.stringify(body),encoded=Buffer.from(public_json,'utf8');if(control.encodingDelay)clock.advance(control.encodingDelay);let stamp=clock.now();
 if(stamp>=id.deadline_ms){body={...body,accepted:false,action:null,checkpoint:false,value:null,error:body.error==='NO_RESPONSE_TIMEOUT'?body.error:'LATE_RESPONSE',late:true};public_json=JSON.stringify(body);encoded=Buffer.from(public_json,'utf8');if(control.rejectionEncodingDelay)clock.advance(control.rejectionEncodingDelay);stamp=clock.now();}
 // Encoded public body is final before stamp. Metadata is not re-encoded for delivery.
 return Object.freeze({...body,stamp_ms:stamp,public_json,public_bytes:encoded.length});
}
module.exports={finalize};
