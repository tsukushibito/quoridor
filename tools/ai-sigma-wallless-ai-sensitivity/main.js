 'use strict';
const walllessRows=[];
function mixed(x,y){return {exact:JSON.stringify(x)===JSON.stringify(y),within_tolerance:x.length===y.length&&x.every((a,i)=>Number.isFinite(a)&&Number.isFinite(y[i])&&Math.abs(a-y[i])<=1e-4+1e-4*Math.abs(y[i])),max_abs:Math.max(...x.map((a,i)=>Math.abs(a-y[i])))};}
async function runWallless(config,inputs,labels){
 for(const engine of ['candidate','reference']){const slot=slotFor(engine),old=slot.worker.onmessage;slot.worker.onmessage=e=>{if(e.data.kind!=='deep_result')return old(e);if(e.data.worker_engine!==engine)throw Error('WORKER_ROUTING');resolveMessage('wallless-'+e.data.id,e.data);};}
 const errors=[];let started=0;
 for(const spec of config.searches){
  const fixture=inputs.find(x=>x.id===spec.fixture_id),state=walllessCheck(fixture),id=config.run_id+'-'+(++started),generation=++generationCounter;
  try{
   await settlePlayerSearches();const wait=waitingMessage('wallless-'+id,15000);const context={generation,key:state._positionKey(),legalActions:state.getLegalActions().map(a=>rustAction(state,a))},shared=SharedBestAction.create(context),control=PlayerControl.create(generation),reader=SharedBestAction.bind(shared,context,context);
   slotFor(spec.engine).worker.postMessage({kind:'deep_search',id,engine:spec.engine,generation,fixture:{...fixture,legal_prefix:fixture.prefix},K:spec.K,timeout_ms:10000,instrumented:false,shared,shared_context:context,control});
   const row=await wait;row.spec=spec;row.SAB_completed=reader.readLatest();row.main_read_ms=epochMain();row.main_control=PlayerControl.bind(control,generation).close('adopt');row.attempt=started;walllessRows.push(row);
   if(row.primary)throw Error(row.primary.message);
   if(row.generation!==generation||row.engine!==spec.engine||row.fixture_id!==fixture.id||row.zero.handles||row.zero.activeNN||row.zero.active)throw Error('GENERATION_ZERO');
   if(!row.SAB_completed||row.SAB_completed.action!==row.cp.action||row.SAB_completed.visits!==spec.K)throw Error('SAB_COMPLETED_BINDING');row.numeric_gate=BrowserNumeric.check({engine:spec.engine,state,numeric:row.numeric[0],cp:row.cp,reference:null});
   row.rootN=spec.engine==='candidate'?row.cp.tree[0].visits:row.cp.root_visits;row.edge_sum=row.cp.root_edges.reduce((s,e)=>s+e[2],0);
   if(row.completed_backups!==spec.K||row.rootN!==spec.K||row.edge_sum!==spec.K-1||row.NN_calls>spec.K)throw Error('TRUE_K_CONVENTION');
   if(spec.K===1&&row.NN_calls!==1)throw Error('ROOT1_NN1');
   row.action_binding=actionBindings(state).find(x=>x.rust_id===row.cp.action);if(!row.action_binding)throw Error('CHOSEN_ACTION_ILLEGAL');
   const label=labels.results.find(x=>x.id===fixture.id).labels;row.certified_interval=label.actions.find(x=>x.action===row.action_binding.label_index)?.interval??null;
   row.winning_set=label.actions.filter(x=>JSON.stringify(x.interval)==='[1,1]').map(x=>x.action);
   row.classification=row.certified_interval?.[0]===1&&row.certified_interval[1]===1?'certifiedwin':row.certified_interval?.[0]===-1&&row.certified_interval[1]===-1?'certifiedloss':'unscored';
   row.score=row.classification==='certifiedwin'?1:row.classification==='certifiedloss'?-1:null;
  }catch(e){const error={spec,name:e.name,message:e.message,stack:e.stack};errors.push(error);if(walllessRows.at(-1))walllessRows.at(-1).main_gate_error=error;break;}
 }
 const comparisons=inputs.map(f=>{const rows=walllessRows.filter(x=>x.fixture_id===f.id&&!x.primary&&!x.main_gate_error),a=rows.find(x=>x.engine==='candidate'&&x.K===32),r=rows.find(x=>x.engine==='reference');if(!a||!r)return {fixture_id:f.id,missing:true};return {fixture_id:f.id,features_exact:JSON.stringify(a.numeric[0].features_bits)===JSON.stringify(r.numeric[0].features_bits),NN:mixed([...a.numeric[0].policy_logits,a.numeric[0].value],[...r.numeric[0].policy_logits,r.numeric[0].value]),candidate_root1_NN:rows.find(x=>x.engine==='candidate'&&x.K===1)?mixed([...a.numeric[0].policy_logits,a.numeric[0].value],[...rows.find(x=>x.engine==='candidate'&&x.K===1).numeric[0].policy_logits,rows.find(x=>x.engine==='candidate'&&x.K===1).numeric[0].value]):null,new_fixedgolden:false};});
 return {rows:walllessRows,errors,started_requests:started,planned:6,completed_requests:walllessRows.filter(x=>!x.primary&&!x.main_gate_error).length,unstarted:6-started,comparisons,games:[],sameK_not_sameNN_CPU_wall:true};
}
