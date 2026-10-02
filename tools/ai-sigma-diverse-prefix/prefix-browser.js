'use strict';
const PREFIX_PLAN=Object.freeze([4,5,8,9,12,13,16,17].map((ply,i)=>({pair:i+1,seed:31001+i,ply})));
function xorshift32(seed){
  let state=seed>>>0;
  if(!state)state=1;
  return ()=>{state^=state<<13;state^=state>>>17;state^=state<<5;state>>>=0;return state;};
}
function prefixFixture(pair,seed,prefix,state){
  const features=state.toNNInput();
  return {id:'diverse-prefix-'+pair,classification:'legal-replay',generation_seed:seed,legal_prefix:structuredClone(prefix),history_count_key:state._positionKey(),history_counts:[...state.position_history].sort((a,b)=>a[0].localeCompare(b[0])),board:{total_ply:state.depth},player:state.getCurrentPlayer(),features_bits:Array.from(new Uint32Array(features.buffer,features.byteOffset,features.length)),legal_ids:state.getLegalActions().map(a=>rustAction(state,a))};
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
function generateDiversePrefixes(){
  const acceptedKeys=new Set(),prefixes=[],attempts=[];
  for(const plan of PREFIX_PLAN){
    let accepted=null;
    for(let attempt=0;attempt<32;attempt++){
      const derived=(plan.seed^Math.imul(0x9e3779b9,attempt))>>>0;
      const seed=derived||1,next=xorshift32(seed),trace=[],prefix=[];
      let state=fromPrefix([]),reason=null;
      for(let ply=0;ply<plan.ply;ply++){
        if(terminalResult(state)){reason='terminal_before_target';break;}
        const legal=state.getLegalActions(),pawn=legal.filter(a=>a.type==='pawn'),wall=legal.filter(a=>a.type==='wall');
        if(!legal.length){reason='no_legal_action';break;}
        // Consume class draw only when both nonempty, then one index draw. Preserve RuleA order within class.
        const classDraw=pawn.length&&wall.length?next():null;
        const type=classDraw===null?(pawn.length?'pawn':'wall'):(classDraw<0x80000000?'pawn':'wall');
        const choices=type==='pawn'?pawn:wall,indexDraw=next(),index=Math.floor(indexDraw/0x100000000*choices.length),action=structuredClone(choices[index]);
        trace.push({ply,class_draw:classDraw,class:type,pawn_count:pawn.length,wall_count:wall.length,index_draw:indexDraw,index,action:structuredClone(action),canonical209:rustAction(state,action)});
        prefix.push(action);state=state.next(action);
      }
      if(!reason&&terminalResult(state))reason='terminal_at_target';
      const key=JSON.stringify(prefix);
      if(!reason&&acceptedKeys.has(key))reason='duplicate_prefix';
      const record={pair:plan.pair,base_seed:plan.seed,attempt,derived_seed:seed,target_ply:plan.ply,prefix,trace,rejection:reason,accepted:!reason};
      attempts.push(record);
      if(!reason){
        const fixture=prefixFixture(plan.pair,seed,prefix,state);diversePrefixState(fixture);
        accepted={pair:plan.pair,accepted:true,base_seed:plan.seed,attempt,fixture};acceptedKeys.add(key);break;
      }
    }
    prefixes.push(accepted??{pair:plan.pair,accepted:false,reason:'32_attempts_exhausted',base_seed:plan.seed});
  }
  const document={issue:'quoridor-4lc.119',PRNG:'xorshift32 unsigned after x<<13,x>>>17,x<<5; nonzero seed',class_rule:'both nonempty: consume one class uint32 (<2^31 pawn, else wall); empty class: no class draw; always consume one uint32 floor(u/2^32*class.length) index in RuleA class order',attempt_rule:'(base XOR Math.imul(0x9e3779b9,attempt)) unsigned; zero to1',selection:'first legal nonterminal nonduplicate exact Action-prefix; no NN/value/AI',search_seed:1979,prefixes,attempts,NN:0,model_loaded:false};
  validateDiverseDocument(document);return document;
}
function validateDiverseDocument(document){
  if(document.issue!=='quoridor-4lc.119'||document.search_seed!==1979)throw Error('PREFIX_DOCUMENT_IDENTITY');
  let P1=0,P2=0;const ids=new Set();
  for(const row of document.prefixes){
    if(!row.accepted)continue;
    if(ids.has(row.fixture.id))throw Error('PREFIX_ID_DUPLICATE');ids.add(row.fixture.id);
    const state=diversePrefixState(row.fixture);
    if(state.getCurrentPlayer()===1)P1++;else P2++;
  }
  return {accepted:ids.size,P1,P2,replay_history_features_legal_order:true,model_or_NN:0,shared_RuleA_independence_limit:true};
}
