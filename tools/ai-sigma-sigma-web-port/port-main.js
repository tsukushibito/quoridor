'use strict';
const portRows=[];
function portMock(){if(PlayerControl===undefined||SharedBestAction===undefined)throw Error('PORT_SHARED_ROUTING');return{two_slots:2,reference_rules_and_retirement_unchanged:true,policy:'Sigma-Web faithful Rust vs original JS',old149_game_execution:false};}
async function runPortMechanism(config,fixtures){
 for(const engine of ['candidate','reference']){const slot=slotFor(engine),original=slot.worker.onmessage;slot.worker.onmessage=e=>{if(e.data.kind==='port_result')resolveMessage('port-'+e.data.id,e.data);else original(e);};}
 const errors=[];
 for(const spec of config.searches){
  const id=config.run_id+'-'+(portRows.length+1),f=fixtures.find(f=>f.id===spec.fixture_id);try{await settlePlayerSearches();const waiter=waitingMessage('port-'+id,15000);slotFor(spec.engine).worker.postMessage({kind:'port_search',id,engine:spec.engine,fixture:f,K:spec.K,generation:++generationCounter,timeout_ms:10000});const row=await waiter;row.spec=spec;portRows.push(row);if(row.primary)throw Error(row.primary.message);if(row.zero.handles||row.zero.activeNN||row.zero.active)throw Error('PORT_NOT_ZERO');if(row.completed!==spec.K||row.cp.root_edges.reduce((s,e)=>s+e[2],0)!==spec.K-1)throw Error('PORT_ROOT_COUNT');row.gate=BrowserNumeric.check({engine:spec.engine,state:fromPrefix(f.legal_prefix),numeric:row.numeric[0],cp:row.cp,reference:null});}catch(e){errors.push({spec,message:e.message,stack:e.stack});break;}
 }
 return{rows:portRows,errors,planned:config.searches.length,started:portRows.length,hand_NN:portRows.reduce((s,r)=>s+r.spans.length,0),sameK_not_sameCPU:true};
}
