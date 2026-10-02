'use strict';
const deepRows=[];
function installDeepHandler(){
  for(const engine of ['candidate','reference']){const slot=slotFor(engine),prior=slot.worker.onmessage;slot.worker.onmessage=event=>{const row=event.data;if(row.kind!=='deep_result')return prior(event);if(row.worker_engine!==engine)throw Error('DEEP_WORKER_BINDING');resolveMessage('deep-'+row.id,row);};}
}
function deepDistribution(row){const sum=row.cp.root_edges.reduce((s,e)=>s+e[2],0);return Object.fromEntries(row.cp.root_edges.map(e=>[e[0],e[2]/sum]));}
function deepTV(a,b){const x=deepDistribution(a),y=deepDistribution(b);return .5*[...new Set([...Object.keys(x),...Object.keys(y)])].reduce((s,k)=>s+Math.abs((x[k]??0)-(y[k]??0)),0);}
function deepMixed(a,b){if(a.length!==b.length)throw Error('TRACE_NN_SHAPE');return {exact:JSON.stringify(a)===JSON.stringify(b),mixed:a.every((v,i)=>Number.isFinite(v)&&Number.isFinite(b[i])&&Math.abs(v-b[i])<=1e-4+1e-4*Math.abs(b[i])),max_abs:Math.max(...a.map((v,i)=>Math.abs(v-b[i])))};}
function canonicalNode(node){return JSON.stringify([node.key,node.ply,[...node.history].sort((a,b)=>a[0].localeCompare(b[0]))]);}
function compareDeepNodes(a,b){
 const pairs=[];
 for(const x of a.trace??[]){const y=(b.trace??[]).find(n=>canonicalNode(n)===canonicalNode(x));if(!y)continue;
 const featuresExact=JSON.stringify(x.features_bits)===JSON.stringify(y.features_bits);
 const nx=x.numeric,ny=y.numeric;
 const numeric=nx&&ny?deepMixed([...(nx.policy_logits??nx.logits),nx.value],[...(ny.policy_logits??ny.logits),ny.value]):null;
 const terminalX=x.terminal,terminalY=y.terminal?.value??null;
 const pathActionsX=x.pre.path.map(e=>e.action),pathActionsY=y.path_actions;
 const backupX=x.post_path.map((e,i)=>({visits_delta:e.edge_visits-x.pre.path[i].edge_visits,value_delta:e.edge_value_sum-x.pre.path[i].edge_value_sum,expected_parent_side_value:x.leaf_side_value*((pathActionsX.length-i)%2?-1:1)}));
 const backupY=y.post_path.map((e,i)=>({visits_delta:e.child_visits-y.pre_path[i].child_visits,parent_edge_value_delta:-(e.child_valueSum-y.pre_path[i].child_valueSum),expected_parent_side_value:y.leaf_side_value*((pathActionsY.length-i)%2?-1:1)}));
 const backupCheck=arr=>arr.every(e=>e.visits_delta===1&&Math.abs((e.value_delta??e.parent_edge_value_delta)-e.expected_parent_side_value)<=1e-4+1e-4*Math.abs(e.expected_parent_side_value));
 pairs.push({key:x.key,ply:x.ply,history_exact:true,features_exact:featuresExact,path_Action_equal:JSON.stringify(pathActionsX)===JSON.stringify(pathActionsY),leaf_turn_equal:x.turn===y.turn,root:x.node_index===0,numeric,terminal_equal:terminalX===terminalY,leaf_value:deepMixed([x.leaf_side_value],[y.leaf_side_value]),candidate_backup:backupX,reference_child_to_parent_edge_backup:backupY,backup_sign_candidate:backupCheck(backupX),backup_sign_reference:backupCheck(backupY),candidate_parentQ_missing:true});
 }
 return {selected_candidate:a.trace?.length??0,selected_reference:b.trace?.length??0,shared:pairs,unshared_candidate:(a.trace?.length??0)-pairs.length,unshared_reference:(b.trace?.length??0)-pairs.length};
}
async function runDeepComparison(config,fixtures,references){
 installDeepHandler();const errors=[],parity=[],comparisons=[];
 const plans=[...config.parity_searches,...config.searches];
 for(const spec of plans){
  if(spec.phase==='primary'&&parity.length!==2)break;
  const fixture=fixtures.find(x=>x.id===spec.fixture_id),engine=spec.engine,id=config.run_id+'-'+(deepRows.length+1),generation=++generationCounter;
  try{
   await settlePlayerSearches();const state=deepCheckedState(fixture);
   const waiting=waitingMessage('deep-'+id,config.count_timeout_ms+5000);
   slotFor(engine).worker.postMessage({kind:'deep_search',id,engine,generation,fixture,K:spec.K,timeout_ms:config.count_timeout_ms,instrumented:spec.instrumented});
   const row=await waiting;row.spec=spec;deepRows.push(row);
   if(row.primary)throw Error(row.primary.message);
   if(row.generation!==generation||row.engine!==engine||row.fixture_id!==fixture.id||row.zero.handles||row.zero.activeNN||row.zero.active)throw Error('DEEP_GENERATION_ZERO');
   row.gate=BrowserNumeric.check({engine,state,numeric:row.numeric[0],cp:row.cp,reference:null});
   row.rootN=engine==='candidate'?row.cp.tree[0].visits:row.cp.root_visits;
   row.edge_sum=row.cp.root_edges.reduce((s,e)=>s+e[2],0);
   if(row.completed_backups!==spec.K||row.rootN!==spec.K||row.edge_sum!==spec.K-1||row.NN_calls>spec.K)throw Error('COMPLETED_K_CONVENTION');
   if(spec.instrumented && (!row.trace||row.trace.length>8))throw Error('TRACE_CAP');
   if(spec.phase==='parity'&&spec.instrumented){
    const original=deepRows.find(x=>x.spec.phase==='parity'&&x.engine===engine&&!x.instrumented);
    const fields=['action','simulations','root_edges','nn_calls','max_depth','cap','root_visits'];
    if(fields.some(k=>JSON.stringify(row.cp[k])!==JSON.stringify(original.cp[k]))||row.NN_calls!==original.NN_calls)throw Error('MEASUREMENT_PARITY');
    parity.push({engine,K:8,CP_Action_visits_NN_depth_caps_exact:true,original_wrapper_ms:original.wrapper_end_ms-original.wrapper_start_ms,instrumented_wrapper_ms:row.wrapper_end_ms-row.wrapper_start_ms,root_NN:deepMixed([...original.numeric[0].policy_logits,original.numeric[0].value],[...row.numeric[0].policy_logits,row.numeric[0].value])});
   }
  }catch(error){const e={spec,name:error.name,message:error.message,stack:error.stack};errors.push(e);if(deepRows.at(-1))deepRows.at(-1).main_gate_error=e;break;}
 }
 for(const fixture of fixtures){const a=deepRows.find(x=>x.spec.phase==='primary'&&x.fixture_id===fixture.id&&x.engine==='candidate'),b=deepRows.find(x=>x.spec.phase==='primary'&&x.fixture_id===fixture.id&&x.engine==='reference');if(!a||!b||a.primary||b.primary||a.main_gate_error||b.main_gate_error)continue;
  const ax=a.numeric[0],bx=b.numeric[0];comparisons.push({fixture_id:fixture.id,root_features_exact:JSON.stringify(ax.features_bits)===JSON.stringify(bx.features_bits),root_NN:deepMixed([...ax.policy_logits,ax.value],[...bx.policy_logits,bx.value]),Action_A:a.cp.action,Action_B:b.cp.action,TV:deepTV(a,b),NN_A:a.NN_calls,NN_B:b.NN_calls,terminal_noNN_A:a.terminal_noNN_backups,terminal_noNN_B:b.terminal_noNN_backups,deep:compareDeepNodes(a,b)});
 }
 return {deep_results:deepRows,errors,parity,comparisons,planned_parity:4,started_parity:deepRows.filter(x=>x.spec.phase==='parity').length,planned_primary:8,started_primary:deepRows.filter(x=>x.spec.phase==='primary').length,completed_primary:deepRows.filter(x=>x.spec.phase==='primary'&&!x.primary&&!x.main_gate_error).length,clock_end:await calibratePlayerClocks(),games:[],sameK_not_sameNN_CPU_wall:true};
}
