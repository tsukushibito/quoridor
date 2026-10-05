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
function portGenerate(plan){
 if(plan.issue!=='quoridor-4lc.151'||plan.slots.length!==8||plan.attempt_cap!==8)throw Error('PORT_GENERATOR_REGISTRATION');
 const prefixes=[],attempts=[],prefixSeen=new Set(),stateSeen=new Set();
 for(const slot of plan.slots){let accepted=null;
  for(let attempt=0;attempt<8;attempt++){
   const seed=slot.attempt_seeds[attempt]>>>0,next=xorshift32(seed),prefix=[],trace=[];let state=fromPrefix([]),reason=null;
   for(let ply=0;ply<slot.layer_ply;ply++){
    if(terminalResult(state)){reason='terminal_before_target';break;}const legal=state.getLegalActions(),pawn=legal.filter(a=>a.type==='pawn'),wall=legal.filter(a=>a.type==='wall');
    if(!legal.length){reason='no_legal_action';break;}const classDraw=pawn.length&&wall.length?next():null,type=classDraw===null?(pawn.length?'pawn':'wall'):(classDraw<0x80000000?'pawn':'wall'),choices=type==='pawn'?pawn:wall,indexDraw=next(),index=Math.floor(indexDraw/0x100000000*choices.length),action=structuredClone(choices[index]);
    if(!legal.some(a=>JSON.stringify(a)===JSON.stringify(action))){reason='illegal_generated_action';break;}
    trace.push({ply,class_draw:classDraw,class:type,index_draw:indexDraw,index,action,canonical209:rustAction(state,action)});prefix.push(action);state=state.next(action);
   }
   if(!reason&&terminalResult(state))reason='terminal_at_target';const signature=trueSignature(state);attempts.push({slot:slot.slot,attempt,seed,prefix,trace,signature,rejection:reason,accepted:!reason});
   if(!reason){const fixture=prefixFixture(slot.slot,seed,prefix,state);fixture.id='port151-prefix-'+slot.slot;diversePrefixState(fixture);accepted={pair:slot.slot,slot:slot.slot,layer_ply:slot.layer_ply,accepted:true,attempt,fixture,signature,duplicate_prefix:prefixSeen.has(JSON.stringify(prefix)),duplicate_true_state:stateSeen.has(signature)};prefixSeen.add(JSON.stringify(prefix));stateSeen.add(signature);break;}
  }
  prefixes.push(accepted??{pair:slot.slot,slot:slot.slot,layer_ply:slot.layer_ply,accepted:false,reason:'8_attempts_exhausted'});
 }
 return{issue:'quoridor-4lc.151',frame:10,seed_table:plan,prefixes,attempts,NN:0,model_loaded:false,selection:'first legal nonterminal; duplicates retained/flagged; no NN/value/policy/result filter; no old149 result integration',shared_RuleA_independence_limit:true};
}
const portInheritedFailure=gameFailureResult;
gameFailureResult=function(classification,currentPlayer,engine,fault){
 if(/ARENA_GUARD_REFUSAL|DEPTH_GUARD_REFUSAL|K_GUARD/.test(fault?.error??''))return{status:'unfinished',winner:null,reason:'port_operational_guard_refusal',fault};
 return portInheritedFailure(classification,currentPlayer,engine,fault);
};
// Extend existing cheap mock to check actual served receiver guard and first-tie ABI.
const portBasicMock=portMock;
portMock=function(config,fixtures){const basic=portBasicMock(),faults=gapMock(config,fixtures);return{...basic,faults,private_guard_nodes:200000,private_guard_depth:200,common_simulation_request_guard:100000,guard_refusal_unfinished:true};};
const portPreviousValidation=validateAfterProgression;
validateAfterProgression=async function(){await portPreviousValidation();for(const row of collectedRows){const cp=row.diagnostic?.validated_cp;
 row.completed_without_NN={count:cp?(row.spec.engine==='reference'?cp.root_visits:cp.simulations)-cp.nn_calls:null,terminal_noNN_direct_count:row.spec.engine==='candidate'?cp?.terminal_noNN??null:null,reference_terminal_noNN_derived:row.spec.engine==='reference'&&cp?cp.root_visits-cp.nn_calls:null,basis:'completed root-inclusive backups minus completed NN on last validated CP; private refusal never pseudo-leaf; reference derived terminal revisits, not independent direct counter',adopted_sequence_counts:row.adoptedCP??null};
 }};
