function frame8Mock(config, fixtures) {
  if(![1979,2098].includes(config.seed))throw Error('REGISTERED_SEED');
  const cases=[];
  for(const fixtureId of ['initial-p1','asym-hv-p2','straight-jump-p2']) {
    const fixture=fixtures.find(row=>row.id===fixtureId);
    let state=fromPrefix([]);
    for(const action of fixture.legal_prefix) {
      const target=rustAction(state,action);
      if(!state.getLegalActions().some(a=>rustAction(state,a)===target))throw Error('PREFIX_ILLEGAL '+fixtureId+' '+JSON.stringify(action));
      state=state.next(action);
    }
    const expected=referenceState(fixture);
    if(state._positionKey()!==expected._positionKey()||terminalResult(state))throw Error('FIXTURE_CONTEXT');
    if(JSON.stringify([...state.position_history])!==JSON.stringify([...expected.position_history]))throw Error('FIXTURE_HISTORY');
    cases.push({fixture:fixtureId,prefix_length:fixture.legal_prefix.length,current_player:state.getCurrentPlayer(),depth:state.depth,key:state._positionKey(),legal:state.getLegalActions().length,history_entries:state.position_history.size});
  }
  const response={completed:false,shared_state:SharedBestAction.STATE.FAULT};
  const fault={error:'NN_BACKEND:DIAGNOSTIC_NN_ERROR'};
  const classification=classifyResponse(response,fault);
  const reference=gameFailureResult(classification,1,'reference',fault);
  const candidate=gameFailureResult(classification,1,'candidate',fault);
  if(reference.reason!=='reference_NN_invalid'||reference.status!=='unfinished'||!reference.pair_invalid)throw Error('REFERENCE_NN_RESPONSIBILITY');
  if(candidate.status!=='responsibility_loss')throw Error('CANDIDATE_NN_RESPONSIBILITY');
  const simultaneous=[{...response,late:true},{...response,judge_error:'DIAGNOSTIC_JUDGE'},{...response,external_abort:{code:'DIAGNOSTIC_ABORT'}}].map(r=>({classification:classifyResponse(r,fault),flags:responseCauses(r,fault)}));
  if(simultaneous.some(r=>r.classification==='engine_fault'))throw Error('SHARED_FAULT_PRIORITY');
  return {fixture_cases:cases,reference,candidate,simultaneous,seed:config.seed,NN:0,scope:'browser-local fixture/history/classification glue, not actual NN failures'};
}
