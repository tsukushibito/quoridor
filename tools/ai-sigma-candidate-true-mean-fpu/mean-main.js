'use strict';
const meanRows=[];
function installMeanHandler(){for(const engine of ['candidate','reference']){const slot=slotFor(engine),prior=slot.worker.onmessage;slot.worker.onmessage=e=>{const row=e.data;if(row.kind!=='mean_result')return prior(e);if(row.worker_engine!==engine)throw Error('MEAN_WORKER_BINDING');resolveMessage('mean-'+row.id,row);};}}
function f32eq(a,b){return Math.fround(a)===Math.fround(b);}
function numericIdentity(n){return {features_bits:n.features_bits,policy_logits:n.policy_logits,value:n.value,legal:n.legal,turn:n.turn,key:n.key,ply:n.ply,history:n.history};}
function exact(a,b){return JSON.stringify(a)===JSON.stringify(b);}
function meanLedgerGate(row){const t=row.trace;if(!t||t.nodes.length>8||t.selections.length>32*24||t.visits.length>32*25)throw Error('MEAN_TRACE_CAP');
 const ledgers=new Map();
 for(const v of t.visits){const prev=ledgers.get(v.node_index)??{N:0,sum:0};if(v.preN!==prev.N||v.preSum!==prev.sum||v.postN!==v.preN+1||!f32eq(v.postSum,Math.fround(Math.fround(v.preSum)+Math.fround(v.value_own_side))))throw Error('TRUE_LEDGER');ledgers.set(v.node_index,{N:v.postN,sum:v.postSum});}
 for(const n of row.cp.tree){const l=ledgers.get(n.index)??{N:0,sum:0};if(l.N!==n.visits||l.sum!==n.true_value_sum)throw Error('LEDGER_NODE_BINDING');}
 for(const s of t.selections){if(!s.nodeN||!f32eq(s.true_mean,Math.fround(Math.fround(s.node_value_sum)/s.nodeN))||s.N0_mean_missing||s.FPU_enabled!==(row.variant==='fpu'))throw Error('MEAN_SELECT_DEFINED');const fpu=Math.fround(Math.fround(s.true_mean)-Math.fround(Math.fround(.2)*Math.fround(Math.sqrt(Math.fround(s.visited_original_prior_sum)))));if(!f32eq(fpu,s.fpu))throw Error('FPU_FORMULA');const q=s.visited?Math.fround(Math.fround(s.edge_value_sum)/s.edge_visits):(row.variant==='fpu'?s.fpu:0);if(!f32eq(q,s.actual_q))throw Error('FPU_ONLY_UNVISITED');}
 for(const n of t.nodes){if(n.post_leaf_visits!==n.pre.leaf_visits+1||!f32eq(n.post_leaf_true_sum,Math.fround(Math.fround(n.pre.leaf_true_sum)+Math.fround(n.leaf_side_value))))throw Error('LEAF_MEAN_SIGN');for(let i=0;i<n.pre.path.length;i++){const a=n.pre.path[i],z=n.post_path[i],v=n.leaf_side_value*((n.pre.path.length-i)%2?-1:1);if(z.parent_visits!==a.parent_visits+1||!f32eq(z.parent_true_sum,Math.fround(Math.fround(a.parent_true_sum)+Math.fround(v)))||z.edge_visits!==a.edge_visits+1||!f32eq(z.edge_value_sum,Math.fround(Math.fround(a.edge_value_sum)+Math.fround(v))))throw Error('ANCESTOR_MEAN_SIGN');}}
 return {actual_node_ledger:true,selects:t.selections.length,selected_unique_nodes:t.nodes.length,N0_real_selects:0,terminal_observed:t.nodes.filter(n=>n.terminal!==null).length};
}
function parityGate(original,q0){
 const fields=['action','simulations','root_edges','nn_calls','max_depth','cap','nodes_count','edges_count','policy_fallbacks','value_fallbacks'];
 const missing=fields.filter(k=>!exact(original.cp[k],q0.cp[k]));
 if(!exact(original.numeric.map(numericIdentity),q0.numeric.map(numericIdentity))||original.NN_calls!==q0.NN_calls||missing.length||!exact(original.CPs.map(r=>r.cp.root_edges),q0.CPs.map(r=>r.cp.root_edges)))throw Error('ORIGINAL_Q0_PARITY_'+missing.join(','));
 return {fixture_id:original.fixture_id,all_root_CP_edges_exact:true,root_features_NN_prior_Action_NN_caps_exact:true,original_arena:original.cp.arena_bytes,instrumented_arena:q0.cp.arena_bytes,layout_cost_not_equal_assumed:true};
}
function distributionTV(a,b){const x=new Map(a.cp.root_edges.map(e=>[e[0],e[2]/31])),y=new Map(b.cp.root_edges.map(e=>[e[0],e[2]/31]));return .5*[...new Set([...x.keys(),...y.keys()])].reduce((s,k)=>s+Math.abs((x.get(k)??0)-(y.get(k)??0)),0);}
async function runMeanComparison(config,fixtures){installMeanHandler();const errors=[],parity=[],comparisons=[];
 for(const spec of config.searches){const fixture=fixtures.find(f=>f.id===spec.fixture_id),id=config.run_id+'-'+(meanRows.length+1),generation=++generationCounter;
  try{await settlePlayerSearches();deepCheckedState(fixture);const w=waitingMessage('mean-'+id,config.count_timeout_ms+5000);slotFor('candidate').worker.postMessage({kind:'mean_search',id,engine:'candidate',variant:spec.variant,generation,fixture,K:32,timeout_ms:config.count_timeout_ms});const row=await w;row.spec=spec;meanRows.push(row);if(row.primary)throw Error(row.primary.message);if(row.generation!==generation||row.fixture_id!==fixture.id||row.zero.handles||row.zero.activeNN||row.zero.active)throw Error('GENERATION_OLD_ZERO');const state=deepCheckedState(fixture);row.numeric_gate=BrowserNumeric.check({engine:'candidate',state,numeric:row.numeric[0],cp:row.cp,reference:null});row.rootN=row.cp.tree[0].visits;row.edge_sum=row.cp.root_edges.reduce((s,e)=>s+e[2],0);if(row.completed_backups!==32||row.rootN!==32||row.edge_sum!==31||row.NN_calls>32||row.CPs.length!==32)throw Error('K32_COUNT');if(spec.variant!=='original')row.mean_gate=meanLedgerGate(row);
  }catch(e){errors.push({spec,message:e.message,stack:e.stack});if(meanRows.at(-1))meanRows.at(-1).main_gate_error=errors.at(-1);break;}
 }
 let branch='unresolved',eligible=[];
 if(meanRows.length===6&&!errors.length){try{
  for(const f of fixtures){const original=meanRows.find(r=>r.fixture_id===f.id&&r.variant==='original'),q0=meanRows.find(r=>r.fixture_id===f.id&&r.variant==='q0'),fpu=meanRows.find(r=>r.fixture_id===f.id&&r.variant==='fpu');parity.push(parityGate(original,q0));if(!exact(q0.numeric.map(numericIdentity),fpu.numeric.map(numericIdentity)))throw Error('SAME_ROOT_EVALUATION');comparisons.push({fixture_id:f.id,original_Action:original.cp.action,Q0_Action:q0.cp.action,FPU_Action:fpu.cp.action,TV:distributionTV(q0,fpu),NN_Q0:q0.NN_calls,NN_FPU:fpu.NN_calls});}
  if(comparisons[0].FPU_Action===133)branch='known_adverse_input3_end';else if(comparisons.every(r=>r.Q0_Action===r.FPU_Action))branch='all_Actions_unchanged_end';else{eligible=comparisons.filter((r,i)=>r.Q0_Action!==r.FPU_Action&&!(i===0?[161,133]:[32,42]).includes(r.FPU_Action));branch=eligible.length?'new_legal_Action_quality_eligible':'only_known_local_Actions_end';}
 }catch(e){errors.push({stage:'parity_quality_branch',message:e.message,stack:e.stack});branch='parity_or_mean_unresolved_end';eligible=[];}}
 return {mean_results:meanRows,errors,parity,comparisons,branch,quality_eligible:eligible,planned_requests:6,started_requests:meanRows.length,completed_requests:meanRows.filter(r=>!r.primary&&!r.main_gate_error).length,unstarted:config.searches.slice(meanRows.length),games:[],clock_end:await calibratePlayerClocks(),sameK_not_sameNN_CPU_wall:true};
}
