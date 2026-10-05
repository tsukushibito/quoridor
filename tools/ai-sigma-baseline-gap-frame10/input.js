'use strict';

function xorshift32(seed){
  let state=seed>>>0;
  if(!state)state=1;
  return ()=>{state^=state<<13;state^=state>>>17;state^=state<<5;state>>>=0;return state;};
}
function prefixFixture(pair,seed,prefix,state){
  const features=state.toNNInput();
  return {id:'frame10-prefix-'+pair,classification:'legal-replay',generation_seed:seed,legal_prefix:structuredClone(prefix),history_count_key:state._positionKey(),history_counts:[...state.position_history].sort((a,b)=>a[0].localeCompare(b[0])),board:{total_ply:state.depth},player:state.getCurrentPlayer(),features_bits:Array.from(new Uint32Array(features.buffer,features.byteOffset,features.length)),legal_ids:state.getLegalActions().map(a=>rustAction(state,a))};
}
function diversePrefixState(fixture){
  const state=fromPrefix(fixture.legal_prefix);
  if(terminalResult(state)||state._positionKey()!==fixture.history_count_key||state.depth!==fixture.board.total_ply||state.getCurrentPlayer()!==fixture.player)throw Error('PREFIX_CONTEXT');
  const history=[...state.position_history].sort((a,b)=>a[0].localeCompare(b[0]));
  if(JSON.stringify(history)!==JSON.stringify(fixture.history_counts))throw Error('PREFIX_HISTORY');
  const features=state.toNNInput();const bits=Array.from(new Uint32Array(features.buffer,features.byteOffset,features.length));
  if(bits.length!==648||JSON.stringify(bits)!==JSON.stringify(fixture.features_bits))throw Error('PREFIX_FEATURE_BITS');
  const legal=state.getLegalActions().map(a=>rustAction(state,a));
  if(JSON.stringify(legal)!==JSON.stringify(fixture.legal_ids))throw Error('PREFIX_LEGAL_ORDER');
  return state;
}
function trueSignature(state){return JSON.stringify({key:state._positionKey(),history_counts:[...state.position_history].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0),side:state.getCurrentPlayer()});}
function generateDiversePrefixes(plan,oldDocument){
 if(plan.issue!=='quoridor-4lc.148'||plan.slots.length!==32||plan.attempt_cap!==8)throw Error('REGISTERED_PLAN');
 const old=oldDocument.prefixes.filter(x=>x.accepted).map(x=>({id:x.fixture.id,state:diversePrefixState(x.fixture)}));
 if(old.length!==8)throw Error('OLD119_EIGHT_REQUIRED');
 const oldSignatures=new Set(old.map(x=>trueSignature(x.state))),prefixes=[],attempts=[],prefixSeen=new Set(),stateSeen=new Set();
 for(const slot of plan.slots){
  if(slot.attempt_seeds.length!==8||slot.search_seed_both!==1979)throw Error('SEED_TABLE_ROW');
  let accepted=null;
  for(let attempt=0;attempt<8;attempt++){
   const seed=slot.attempt_seeds[attempt]>>>0,next=xorshift32(seed),prefix=[],trace=[];let state=fromPrefix([]),reason=null;
   for(let ply=0;ply<slot.layer_ply;ply++){
    if(terminalResult(state)){reason='terminal_before_target';break;}
    const legal=state.getLegalActions(),pawn=legal.filter(a=>a.type==='pawn'),wall=legal.filter(a=>a.type==='wall');
    if(!legal.length){reason='no_legal_action';break;}
    const classDraw=pawn.length&&wall.length?next():null;
    const type=classDraw===null?(pawn.length?'pawn':'wall'):(classDraw<0x80000000?'pawn':'wall');
    const choices=type==='pawn'?pawn:wall,indexDraw=next(),index=Math.floor(indexDraw/0x100000000*choices.length),action=structuredClone(choices[index]);
    if(!legal.some(a=>JSON.stringify(a)===JSON.stringify(action))){reason='illegal_generated_action';break;}
    trace.push({ply,class_draw:classDraw,class:type,pawn_count:pawn.length,wall_count:wall.length,index_draw:indexDraw,index,action:structuredClone(action),canonical209:rustAction(state,action)});
    prefix.push(action);state=state.next(action);
   }
   if(!reason&&terminalResult(state))reason='terminal_at_target';
   const signature=trueSignature(state);if(!reason&&oldSignatures.has(signature))reason='old119_true_state_signature';
   attempts.push({slot:slot.slot,attempt,seed,target_ply:slot.layer_ply,prefix,trace,signature,rejection:reason,accepted:!reason});
   if(!reason){const fixture=prefixFixture(slot.slot,seed,prefix,state);diversePrefixState(fixture);
    accepted={pair:slot.slot,slot:slot.slot,layer_ply:slot.layer_ply,block:slot.block,replicate:slot.replicate,accepted:true,attempt,fixture,signature,duplicate_prefix:prefixSeen.has(JSON.stringify(prefix)),duplicate_true_state:stateSeen.has(signature),all_attempt_seeds:slot.attempt_seeds};
    prefixSeen.add(JSON.stringify(prefix));stateSeen.add(signature);break;}
  }
  prefixes.push(accepted??{pair:slot.slot,slot:slot.slot,layer_ply:slot.layer_ply,accepted:false,reason:'8_attempts_exhausted',all_attempt_seeds:slot.attempt_seeds});
 }
 const document={issue:'quoridor-4lc.149',frame:10,search_seed:1979,seed_table:plan,old119_signatures:old.map(x=>({id:x.id,signature:trueSignature(x.state),features_bits:prefixFixture(0,0,[],x.state).features_bits})),prefixes,attempts,NN:0,model_loaded:false,selection:'first legal nonterminal not any old119 true signature; new duplicates retained/flagged; no AI/model/prior/value filter',PRNG:'xorshift32 same unsigned 119 shifts; consume class draw only when both nonempty then one index draw; class half, uniform index in original RuleA order'};
 validateDiverseDocument(document);return document;
}
function validateDiverseDocument(document){
  if(document.issue!=='quoridor-4lc.149'||document.search_seed!==1979)throw Error('PREFIX_DOCUMENT_IDENTITY');
  let P1=0,P2=0;const ids=new Set();
  for(const row of document.prefixes){
    if(!row.accepted)continue;
    if(ids.has(row.fixture.id))throw Error('PREFIX_ID_DUPLICATE');ids.add(row.fixture.id);
    const state=diversePrefixState(row.fixture);
    if(state.getCurrentPlayer()===1)P1++;else P2++;
  }
  return {accepted:ids.size,P1,P2,replay_history_features_legal_order:true,model_or_NN:0,shared_RuleA_independence_limit:true};
}
