'use strict';
function deepFixture(input){
  const state=fromPrefix(input.legal_prefix);if(terminalResult(state))throw Error('MID_INPUT_TERMINAL');
  const bits=state.toNNInput();
  return {...input,classification:'legal-replay',board:{total_ply:state.depth,walls_remaining:[state.walls_p1,state.walls_p2],turn:state.isPlayer1Turn()?0:1},history_count_key:state._positionKey(),history_counts:[...state.position_history].sort((a,b)=>a[0].localeCompare(b[0])),features_bits:Array.from(new Uint32Array(bits.buffer,bits.byteOffset,bits.length)),legal_ids:state.getLegalActions().map(a=>rustAction(state,a))};
}
function deepCheckedState(fixture){
  const observed=deepFixture(fixture);for(const name of ['board','history_count_key','history_counts','features_bits','legal_ids'])if(JSON.stringify(observed[name])!==JSON.stringify(fixture[name]))throw Error('DEEP_INPUT_BINDING_'+name);
  if(observed.board.total_ply!==fixture.original_prefix_plies+fixture.new_public_plies)throw Error('TOTAL_VS_NEW_PLY');return fromPrefix(fixture.legal_prefix);
}

function deepRustPrefix(prefix){let state=fromPrefix([]);const ids=[];for(const action of prefix){ids.push(rustAction(state,action));state=state.next(action);}return ids;}
