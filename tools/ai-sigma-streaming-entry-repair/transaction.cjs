const now=()=>Number(process.hrtime.bigint())/1e6;
/** Unique ID is created before send; producer echoes the ID of its actual input. No host-created response identity. */
function guardTransaction({engine,req,t0,T,send,abort,event=()=>{}}){
 let settled=false,timer,cancel; const deadline=t0+T;
 const promise=new Promise(resolve=>{
  const settle=(v)=>{if(settled){event({kind:'duplicate_or_old_response',engine,request_id:req.request_id,at_ms:now()});return;}settled=true;clearTimeout(timer);resolve(v);};
  const stop=(code,detail)=>{if(settled)return;settled=true;clearTimeout(timer);const at=now();
   const output={transaction_error:code,detail,discarded:true,request_id:req.request_id,watchdog_at_ms:at,overshoot_ms:Math.max(0,at-deadline),cleanup_status:'pending; reuse forbidden'};
   // Public timeout is completed immediately. Stop/wait continues as owned cleanup, never adoption grace.
   let cleanup;try{cleanup=Promise.resolve(abort());}catch(e){cleanup=Promise.reject(e)}
   cleanup.then(()=>{output.cleanup_status='completed';output.cleanup_end_ms=now();event({kind:'owned_cleanup_completed',engine,request_id:req.request_id,at_ms:output.cleanup_end_ms});},e=>{output.cleanup_status='failed';output.cleanup_error=e.message;event({kind:'owned_cleanup_error',engine,error:e.message});});
   resolve(output);
  };
  cancel=()=>stop('cancelled','explicit host generation invalidation; old response rejected');const watch=()=>{const remaining=deadline-now();if(remaining>0){timer=setTimeout(watch,Math.ceil(remaining));return;}stop('NO_RESPONSE_TIMEOUT','reason pending: deadline reached without verified response');};timer=setTimeout(watch,Math.max(0,Math.ceil(deadline-now())));
  Promise.resolve().then(send).then(q=>{
   if(settled){event({kind:'late_or_duplicate_response_discarded',raw:q,at_ms:now()});return;}
   const envelope=q?.payload,identity=envelope?.transaction;
   if(!identity||identity.request_id!==req.request_id||identity.generation!==req.generation){void stop('IDENTITY_MISMATCH',{expected:{request_id:req.request_id,generation:req.generation},actual:identity??null,raw:q});return;}
   if(['candidate','reference'].includes(engine)&&(identity.engine!==engine||['prefix','legal_prefix','seed','simulations','max_nodes','max_depth','T_ms','g_ms'].some(k=>JSON.stringify(identity[k])!==JSON.stringify(req[k])))){void stop('IDENTITY_MISMATCH',{expected_prefix:req.prefix,actual:identity});return;}
   const producerGen=engine==='reference'?envelope.generation:engine==='candidate'?envelope.generation:envelope.data?.generation;
   if(producerGen!==undefined&&producerGen!==req.generation){void stop('IDENTITY_MISMATCH',{producer_generation:producerGen,raw:q});return;}
   if(now()>=deadline){void stop('LATE_RESPONSE',q);return;}
   settle(q);
  },e=>void stop(e.message==='BACKEND_EXIT'?'BACKEND_EXIT':'PIPE_ERROR',{message:e.message,code:e.code,signal:e.signal}));
 });promise.cancel=()=>cancel();return promise;
}
module.exports={guardTransaction,now};
