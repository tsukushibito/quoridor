'use strict';
const countRows=[];
let countHandlerInstalled=false;
function installCountHandler(){
  if(countHandlerInstalled)return;
  for(const engine of ['candidate','reference']){
    const slot=slotFor(engine),prior=slot.worker.onmessage;
    slot.worker.onmessage=event=>{
      const row=event.data;
      if(row.kind!=='count_result')return prior(event);
      if(row.worker_engine!==engine)throw Error('COUNT_PLAYER_BINDING');
      resolveMessage('count-'+row.id,row);
    };
  }
  countHandlerInstalled=true;
}
function countFixtureState(fixture){return checkedCountState(fixture);}
function rootDistribution(row){
  const sum=row.cp.root_edges.reduce((s,e)=>s+e[2],0);
  return Object.fromEntries(row.cp.root_edges.map(e=>[String(e[0]),e[2]/sum]));
}
function totalVariation(left,right){
  const a=rootDistribution(left),b=rootDistribution(right);
  return .5*Object.keys(a).reduce((s,id)=>s+Math.abs(a[id]-b[id]),0);
}
function compareRootNumeric(a,b){
  const x=a.numeric[0],y=b.numeric[0];
  if(JSON.stringify(x.features_bits)!==JSON.stringify(y.features_bits))throw Error('SAME_INPUT_FEATURE_BITS');
  const max=Math.max(...x.policy_logits.map((v,i)=>Math.abs(v-y.policy_logits[i])),Math.abs(x.value-y.value));
  const exact=JSON.stringify(x)===JSON.stringify(y);
  for(const [v,r] of [...x.policy_logits.map((v,i)=>[v,y.policy_logits[i]]),[x.value,y.value]])if(Math.abs(v-r)>1e-4+1e-4*Math.abs(r))throw Error('SAME_INPUT_ROOT_NN');
  return {features648_exact:true,NN137_mixed:true,NN_exact:exact,max_abs:max};
}
async function runCompletedFPU(config,fixtures,references){
  installCountHandler();
  const errors=[];
  for(const spec of config.searches){
    if(errors.length)break;
    const fixture=fixtures.find(x=>x.id===spec.fixture_id),engine=spec.condition==='A'?'candidate':'reference';
    if(!fixture)throw Error('COUNT_FIXTURE_MISSING');
    const state=countFixtureState(fixture),id=config.run_id+'-'+(countRows.length+1),generation=++generationCounter;
    const reply=waitingMessage('count-'+id,config.count_timeout_ms+5000);
    slotFor(engine).worker.postMessage({kind:'count_search',id,engine,generation,condition:spec.condition,fixture,prefix:fixture.id.startsWith('diverse-prefix-')?rustPrefix(fixture.legal_prefix):null,K:config.K,timeout_ms:config.count_timeout_ms});
    const row=await reply;countRows.push(row);
    try{
      if(row.primary)throw Error(row.primary.message);
      if(row.generation!==generation || row.condition!==spec.condition || row.fixture_id!==fixture.id)throw Error('COUNT_REQUEST_BINDING');
      if(row.zero.handles || row.zero.activeNN || row.zero.active || row.zero.mode!=='original')throw Error('COUNT_ZERO_MODE');
      row.gate=BrowserNumeric.check({engine,state,numeric:row.numeric[0],cp:row.cp,reference:references.find(x=>x.id===fixture.id)});
      row.edge_sum=row.cp.root_edges.reduce((s,e)=>s+e[2],0);
      row.observed_root_N=engine==='candidate'?row.cp.tree[0].visits:row.root_node.truevisitCount;
      if(row.completed_backups!==config.K || row.observed_root_N!==config.K || row.edge_sum!==config.K-1)throw Error('COUNT_K_CONVENTION');
      if(engine==='reference' && (row.cp.simulations!==config.K-1 || row.cp.root_visits!==config.K))throw Error('REFERENCE_LOOP31');
      row.entropy=row.cp.root_edges.reduce((s,e)=>e[2]?s-e[2]/row.edge_sum*Math.log(e[2]/row.edge_sum):s,0);
      row.main_received_ms=epochMain();
      row.depth=engine==='candidate'?row.cp.max_depth:row.reference_visited_depth??null;row.caps=engine==='candidate'?row.cp.cap:null;
    }catch(error){row.main_gate_error={name:error.name,message:error.message};errors.push(row.main_gate_error);}
  }
  const comparisons=[];
  for(const fixture_id of config.input_order){
    const group=Object.fromEntries(countRows.filter(x=>x.fixture_id===fixture_id).map(x=>[x.condition,x]));
    if(!['A','B','C'].every(k=>group[k] && !group[k].primary && !group[k].main_gate_error))continue;
    comparisons.push({fixture_id,root_inputs_AB:compareRootNumeric(group.A,group.B),root_inputs_BC:compareRootNumeric(group.B,group.C),TV_AB:totalVariation(group.A,group.B),TV_AC:totalVariation(group.A,group.C),TV_BC:totalVariation(group.B,group.C),actions:Object.fromEntries(['A','B','C'].map(k=>[k,group[k].cp.action])),wrapper_ms:Object.fromEntries(['A','B','C'].map(k=>[k,group[k].wrapper_end_ms-group[k].wrapper_start_ms])),NN_calls:Object.fromEntries(['A','B','C'].map(k=>[k,group[k].NN_calls]))});
  }
  return {count_results:countRows,comparisons,errors,planned:config.searches.length,started:countRows.length,completed:countRows.filter(x=>!x.primary&&!x.main_gate_error).length,unstarted:config.searches.length-countRows.length,game_started:0,Node_per_hand_judge:0,clock_end:await calibratePlayerClocks(),sameK_not_sameNN_CPU_wall:true};
}
