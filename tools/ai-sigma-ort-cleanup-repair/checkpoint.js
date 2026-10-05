/* Research-only clock adapter. No Rust/NN/search changes. */
(function(root){
 const copy=v=>JSON.parse(JSON.stringify(v));
 function freeze(v){if(v&&typeof v==='object'){for(const x of Object.values(v))freeze(x);Object.freeze(v)}return v}
 function validateDelivery(r,{generation,request_id,now,deadline,legal,fixture,prefix,clock}){
  if(fixture!==undefined&&JSON.stringify(r.owned?.identity.fixture)!==JSON.stringify(fixture)||prefix!==undefined&&JSON.stringify(r.owned?.identity.prefix)!==JSON.stringify(prefix))return false;
  if(r.error||!r.owned||r.owned.identity.generation!==generation||r.owned.identity.request_id!==request_id||now>=deadline||r.owned.completed_at>=deadline||r.cp.policy_fallbacks||r.cp.value_fallbacks||r.fallback||(r.cp.terminal_value==null&&r.cp.action==null)||r.cp.action!=null&&!legal.includes(r.cp.action))return false;
  if(!Array.isArray(r.cp.root_edges)||r.cp.root_edges.some(e=>e.length!==4||e.some(x=>!Number.isFinite(x))||e[1]<0||!Number.isInteger(e[2])||e[2]<0))return false;
  const exact=JSON.stringify(r.cp)===JSON.stringify(r.owned.cp);return exact&&(!clock||clock()<deadline);
 }
 async function runOwned(d,env){
  const {b,epoch,yieldTask,getGeneration,notify}=env;
  const t=d.t0??epoch(),deadline=t+(d.T_ms??1e9),stop=deadline-(d.g_ms??0),g=d.generation;
  let s=null,owned=null,cp=null,calls=0,completedNN=0,pendingToken=null,lastToken=null,budgetStop=null,legal=[],terminal=null;
  const spans=[],trace=[];
  const check=()=>{if(g!==getGeneration())throw Error('STALE_GENERATION');if(epoch()>=deadline)throw Error('DEADLINE')};
  const close=()=>{if(s!=null){const h=s;s=null;b.free(h)}};
  const inject=async(phase)=>{if(env.hook)await env.hook(phase,{s,cp,owned,calls,pendingToken});if(d.inject_phase===phase&&d.inject_after_sim===cp?.simulations){if(d.inject_kind==='fault')throw Error('INJECTED_HARDFAULT');if(d.inject_kind==='delay')await new Promise(r=>setTimeout(r,d.inject_until_guard?Math.max(0,stop+2-epoch()):(d.inject_delay_ms??500)))}};
  try{
   check();if(epoch()>=stop)throw Error('NO_CHECKPOINT');
   const req={fixture:d.fixture,prefix:d.prefix,diagnostic:true,simulations:d.simulations??4096,max_nodes:d.max_nodes??512,max_depth:d.max_depth??24,generation:g,seed:1979};
   const identity=freeze(copy({request_id:d.request_id,generation:g,fixture:d.fixture??null,prefix:d.prefix??null,seed:1979,simulations:req.simulations,max_nodes:req.max_nodes,max_depth:req.max_depth}));
   const rootStart=epoch();s=b.create(req);const raw=b.call({op:'raw',fixture:d.fixture??{prefix:d.prefix}});legal=copy(raw.effective_legal);terminal=raw.terminal;spans.push({kind:'root',start:rootStart,end:epoch()});check();
   while(true){
    check();if(epoch()>=stop){budgetStop='before_begin';break}
    const begin=epoch();let done;const q=b.call({op:'begin',handle:s,generation:g});pendingToken=q.pending?q.token:null;
    spans.push({kind:'begin_feature_request',start:begin,end:epoch(),token:pendingToken});
    await inject('after_begin');check();
    if(q.pending){
     if(epoch()>=stop){budgetStop='begin_crossed_guard';break}
     if(d.notify&&calls===(d.notify_after_sim??0))notify({kind:'nn_started',generation:g,request_id:d.request_id});
     const nnstart=epoch();calls++;let r;
     try{if(d.inject_nn_error)throw Error('INJECTED_NN_ERROR');r=await b.infer(q.features_bits);spans.push({kind:'NN',token:q.token,start:nnstart,end:epoch(),nn_ms:r.nn_ms})}catch(e){spans.push({kind:'NNerror',token:q.token,start:nnstart,end:epoch(),error:e.message});throw e}
     if(d.stepdelay_ms)await new Promise(resolve=>setTimeout(resolve,d.stepdelay_ms));
     check();await inject('before_resume');check();const resumeStart=epoch();
     const st=b.call({op:'resume',handle:s,generation:g,token:q.token,logits:r.logits,value:r.value});
     completedNN++;lastToken=q.token;pendingToken=null;spans.push({kind:'resume_policy_backup',start:resumeStart,end:epoch()});check();done=st.done;
    }else done=q.done;
    await inject('before_checkpoint');check();const finishStart=epoch();
    const complete=b.call({op:d.capture_tree?'snapshot':'checkpoint',handle:s,generation:g});
    if(complete.policy_fallbacks||complete.value_fallbacks)throw Error('NN_FALLBACK');
    if(complete.action!=null&&!legal.includes(complete.action)||complete.action==null&&terminal==null)throw Error('INVALID_CHECKPOINT');
    check();const candidate=freeze(copy({identity,cp:complete,completed_at:epoch(),completed_token:lastToken,completed_NN:completedNN,NN_attempts:calls}));check();owned=candidate;cp=owned.cp;
    spans.push({kind:'finish_owned_copy',start:finishStart,end:epoch()});if(d.capture_trace)trace.push(copy(owned));
    spans.push({kind:'step',start:begin,end:epoch(),sims:cp.simulations});await yieldTask();check();if(done)break;
   }
   // Cancel any pending begin; never call checkpoint/finish on the changed tree.
   if(budgetStop){if(pendingToken!=null)b.call({op:'cancel',handle:s,generation:g});close();check();if(!owned)throw Error('NO_CHECKPOINT')}
   await inject('before_return');check();close();check();
   return{cp,owned,calls,completed_NN:completedNN,pending_NN:0,invalidated_pending_token:pendingToken,budget_stop:budgetStop,trace,spans,t0:t,worker_finish:epoch(),error:null,fallback:0,memory:b.e.memory.buffer.byteLength,live_searches:0};
  }catch(error){owned=null;cp=null;if(s!=null)try{b.call({op:'cancel',handle:s,generation:g})}catch{};try{close()}catch(e){error=Error('CLEANUP_'+e.message)}
   return{error:error.message,cp:null,owned:null,calls,completed_NN:completedNN,spans,trace:[],t0:t,worker_finish:epoch(),fallback:0,live_searches:s==null?0:1};
  }finally{close()}
 }
 const api={runOwned,validateDelivery};if(typeof module!=='undefined')module.exports=api;Object.assign(root,api);
})(globalThis);
