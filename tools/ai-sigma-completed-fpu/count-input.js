'use strict';
function checkedCountState(fixture){
  if(!fixture.id.startsWith('diverse-prefix-'))return referenceState(fixture);
  const state=fromPrefix(fixture.legal_prefix);
  const input=state.toNNInput();
  const bits=Array.from(new Uint32Array(input.buffer,input.byteOffset,input.length));
  const history=[...state.position_history].sort((a,b)=>a[0].localeCompare(b[0]));
  const legal=state.getLegalActions().map(a=>rustAction(state,a));
  if(state.depth!==fixture.board.total_ply || state._positionKey()!==fixture.history_count_key || JSON.stringify(history)!==JSON.stringify(fixture.history_counts) || JSON.stringify(bits)!==JSON.stringify(fixture.features_bits) || JSON.stringify(legal)!==JSON.stringify(fixture.legal_ids))throw Error('COUNT_PREFIX_CONTEXT_FEATURE_LEGAL');
  if(terminalResult(state))throw Error('COUNT_INPUT_TERMINAL');
  return state;
}
