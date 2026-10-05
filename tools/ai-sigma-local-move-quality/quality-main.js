'use strict';
const QUALITY_POLICY='fixedSigma C1/FPU.2/first/temp0/originalorder';
function qualityForce(selected,branch){
 const fixture=selected.fixture,state=deepCheckedState(fixture),saved=selected[branch],cp=saved.cp;
 if(state.getCurrentPlayer()!==2||state.walls_p1!==fixture.board.walls_remaining[0]||state.walls_p2!==fixture.board.walls_remaining[1])throw Error('ORIGINAL_WALLS_SIDE');
 if(cp.action!==saved.Action209||!cp.root_edges.some(e=>e[0]===cp.action))throw Error('ORIGINAL_CP_ACTION');
 const actions=state.getLegalActions(),ids=actions.map(a=>rustAction(state,a));
 if(JSON.stringify(cp.root_edges.map(e=>e[0]).sort((a,b)=>a-b))!==JSON.stringify(ids.slice().sort((a,b)=>a-b)))throw Error('ORIGINAL_CP_LEGAL');
 const index=ids.indexOf(saved.Action209);if(index<0)throw Error('FORCED_ACTION_ILLEGAL');
 const action=structuredClone(actions[index]),next=state.next(action),prefix=[...structuredClone(fixture.legal_prefix),action];
 const replay=fromPrefix(prefix);
 if(next._positionKey()!==replay._positionKey()||JSON.stringify([...next.position_history])!==JSON.stringify([...replay.position_history])||next.depth!==fixture.board.total_ply+1)throw Error('FORCED_REPLAY');
 const permutation=BrowserNumeric.expected(state).indices;
 return {state:next,prefix,forced:{branch,source_engine:saved.source_engine,source_K:32,Action209:saved.Action209,Action:action,P2canonical_policy_index:permutation.get(saved.Action209),side:2,NN:0,
   original_key:state._positionKey(),branch_key:next._positionKey(),prefix_length:fixture.legal_prefix.length,totalply_before:state.depth,totalply_after:next.depth,
   walls_before:[state.walls_p1,state.walls_p2],walls_after:[next.walls_p1,next.walls_p2],history_counts:[...next.position_history].sort((a,b)=>a[0].localeCompare(b[0])),terminal:terminalResult(next)}};
}
function qualityPreflight(document){
 if(document.issue!=='quoridor-4lc.134'||document.rollouts.length!==8)throw Error('QUALITY_PLAN');
 const branches=[];
 for(const selected of document.selected)for(const branch of ['A','B'])branches.push({input_index:selected.input_index,forced:qualityForce(selected,branch).forced});
 const cases=[];
 for(const engine of ['candidate','reference']){
  const fault={error:'NN_BACKEND:MOCK_FAILURE'};
  const base={completed:false,shared_state:SharedBestAction.STATE.FAULT};
  const failure=gameFailureResult(classifyResponse(base,fault),1,engine,fault);
  if(failure.reason!=='reference_NN_invalid'||failure.status!=='unfinished'||!failure.pair_invalid)throw Error('BOTH_REFERENCE_NN_INVALID');
  const combined=[{...base,late:true},{...base,judge_error:'MOCK_JUDGE'},{...base,external_abort:{code:'MOCK_ABORT'}}].map(r=>({classification:classifyResponse(r,fault),flags:responseCauses(r,fault)}));
  if(combined.some(x=>x.classification==='engine_fault'))throw Error('SHARED_PRIORITY');
  cases.push({engine,policy:QUALITY_POLICY,failure,combined});
 }
 return {branches,cases,NN:0,models:0,both_reference_policy:true,Action_and_P2_from_actual_legal:true,history_replay_exact:true,clock: {T:500,cutoff:402,adopt:411},independent_transport_slots:true};
}
async function qualityConnections(config,document){
 const selected=document.selected.find(x=>x.input_index===3),branch=qualityForce(selected,'A');
 for(const engine of ['candidate','reference']){
  await settlePlayerSearches();
  const {row}=await chooseBrowser({engine,cancel:false,functional:true,numeric_selected:true,physical_side:engine==='candidate'?1:2,policy:QUALITY_POLICY},branch.state,branch.prefix,null,config);
  if(row.response.classification!=='completed_legal')throw Error('CONNECTION_'+row.response.classification);
 }
 await validateAfterProgression();
 const rows=collectedRows.filter(r=>r.spec.functional);
 if(rows.length!==2)throw Error('CONNECTION_DENOMINATOR');
 const left=rows[0].diagnostic.numeric[0],right=rows[1].diagnostic.numeric[0];
 if(JSON.stringify(left.features_bits)!==JSON.stringify(right.features_bits))throw Error('SAMEINPUT_FEATURES');
 const a=[...left.policy_logits,left.value],b=[...right.policy_logits,right.value];
 if(a.some((x,i)=>Math.abs(x-b[i])>1e-4+1e-4*Math.abs(b[i])))throw Error('SAMEINPUT_NN');
 return {rows:2,completed_legal:2,sameinput_features648:true,sameinput_NN137:true,game_input_not_advanced:true,both_actual_search_policy:QUALITY_POLICY};
}
async function runQualityRollouts(config,document){
 const connection=config.connection?await qualityConnections(config,document):null;
 for(const planned of config.games){
  if(externalAbort||Date.now()>=Date.parse(config.processing_deadline))break;
  const selected=document.selected.find(x=>x.input_index===planned.input_index);
  let {state,prefix,forced}=qualityForce(selected,planned.branch);
  const game={...planned,initial_prefix:structuredClone(selected.fixture.legal_prefix),forced,policy_players:[QUALITY_POLICY,QUALITY_POLICY],actions:[],turn_indices:[],numeric_selected:[],status:'started',winner:null,reason:null,forced_side_score:null,start_ms:epochMain()};
  collectedGames.push(game);startedGames++;
  const seen=new Set(),wallTimer=setTimeout(()=>browserAbort({code:'ROLLOUT_WALL_TIMEOUT',game_id:game.id,scope:'browser/automation unfinished, not engine loss'}),planned.external_wall_seconds*1000);
  pendingTimers.add(wallTimer);
  try{
   while(!terminalResult(state)){
    if(externalAbort){game.status='unfinished';game.reason=externalAbort.code;break;}
    const side=state.getCurrentPlayer(),engine=side===1?'candidate':'reference',numeric_selected=!seen.has(side);
    const {row,nextState}=await chooseBrowser({engine,cancel:false,game_id:game.id,turn:game.actions.length,physical_side:side,policy:QUALITY_POLICY,numeric_selected},state,prefix,null,config);
    game.turn_indices.push(row.identity.request_id);
    if(numeric_selected){seen.add(side);game.numeric_selected.push(row.identity.request_id);}
    if(row.response.classification!=='completed_legal'){
     Object.assign(game,gameFailureResult(row.response.classification,side,engine,row.response.causes.received_fault));break;
    }
    const action=structuredClone(row.response.body.action);game.actions.push(action);prefix.push(action);state=nextState;
   }
   const terminal=terminalResult(state);
   if(terminal){game.status='terminal';game.winner=terminal.winner;game.reason=terminal.winner?'goal':'RuleA_draw';game.forced_side_score=terminal.winner===0?.5:terminal.winner===forced.side?1:0;}
   else if(game.status==='responsibility_loss')game.forced_side_score=game.winner===forced.side?1:0;
   game.total_ply=state.depth;game.new_public=game.actions.length;game.final_key=state._positionKey();game.final_history=[...state.position_history];game.final_walls=[state.walls_p1,state.walls_p2];
  }catch(error){game.status='unfinished';game.reason='browser_infrastructure_failure';game.error={name:error.name,message:error.message};}
  finally{clearTimeout(wallTimer);pendingTimers.delete(wallTimer);}
  await settlePlayerSearches();
  await validateAfterProgression(); // Diagnostics and selected numeric gates only after rollout; no opponent-t0 work.
  // RuleA replay is browser-local post-rollout verification; Node does not judge or replay.
  let replay=fromPrefix([...game.initial_prefix,game.forced.Action]);
  for(const action of game.actions){if(!replay.getLegalActions().some(a=>rustAction(replay,a)===rustAction(replay,action)))throw Error('ROLLOUT_REPLAY_ILLEGAL');replay=replay.next(action);}
  game.browser_replay={legal_public:game.actions.length,final_key_exact:replay._positionKey()===game.final_key,history_exact:JSON.stringify([...replay.position_history])===JSON.stringify(game.final_history),terminal:terminalResult(replay)};
  if(!game.browser_replay.final_key_exact||!game.browser_replay.history_exact)throw Error('ROLLOUT_REPLAY_STATE');
  game.end_ms=epochMain();game.search_zero_before_next_branch=true;
  if(game.status==='unfinished')break;
 }
 return {...collectBrowser(),connection,planned_games:config.games.length,policy_players:[QUALITY_POLICY,QUALITY_POLICY],score_is_forced_side_not_candidate_AI:true};
}
