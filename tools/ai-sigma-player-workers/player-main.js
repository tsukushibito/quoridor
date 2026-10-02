'use strict';
const playerSlots = new Map();
const pendingCleanups = new Set();
const deferredChecks = new Map();
const playerErrors = [];
let generationCounter = 0;
const waitingMessages = new Map();
const privateDiagnostics = new Map();
const requestFaults = new Map();
const collectedRows=[];
let startupRows=[];
let startedRequests=0;
let startedGames=0;
let pendingTimers=new Set();
let lastOwnedACK=null;
let activeMainState=null;
let workerClock={lo_ms:0,hi_ms:0,mid_ms:0,error_ms:0,measured:false};
let externalAbort=null;
const collectedGames=[];
let currentReader=null;
let currentGeneration=null;
const epochMain = ()=>performance.timeOrigin+performance.now();
function waitingMessage(key,timeoutMs=8000) {
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{waitingMessages.delete(key);reject(Error('BROWSER_MESSAGE_TIMEOUT_'+key));},timeoutMs);
    waitingMessages.set(key,{resolve,reject,timer});
  });
}
function resolveMessage(key, value) {
  const pending=waitingMessages.get(key);
  if (pending) { clearTimeout(pending.timer);waitingMessages.delete(key);pending.resolve(value); }
}
function slotFor(engine) {
  const slot=playerSlots.get(engine);
  if(!slot) throw Error('PLAYER_ENGINE_BINDING');
  return slot;
}
function setupEarly() {
  for(const engine of ['candidate','reference']) {
    const slot={engine,worker:new Worker('/early-worker.js?engine='+engine),cleanup:Promise.resolve(),busy:false,
      reader:null,control:null,current:null,lastACK:null,clock:{lo_ms:0,hi_ms:0,mid_ms:0,error_ms:0,measured:false}};
    playerSlots.set(engine,slot);
    slot.worker.onmessage=({data:message})=>{
      if(message.worker_engine!==engine || message.identity && message.identity.engine!==engine) {
        playerErrors.push({engine,cause:'PLAYER_MESSAGE_BINDING',at_ms:epochMain()});
        browserAbort({code:'PLAYER_MESSAGE_BINDING'});return;
      }
      if(message.kind==='fault') requestFaults.set(message.identity.request_id,{error:message.error,at_ms:epochMain(),worker_fault_ms:message.producer_fault_ms});
      else if(message.kind==='retired_result_discarded') slot.retirement=message;
      else if(message.kind==='private_done') {privateDiagnostics.set(message.identity.request_id,message);resolveMessage('private-'+message.identity.request_id,message);}
      else if(message.kind==='stopped') resolveMessage('stop-'+message.identity.request_id,{...message,main_received_ms:epochMain()});
      else if(['startup_root','ready','failed','dropped','ping'].includes(message.kind)) {
        const key=message.kind==='startup_root'?'startup-root':message.kind==='failed'?'ready':message.kind;
        resolveMessage(engine+'-'+key,message);
      }
    };
    slot.worker.onerror=event=>{
      playerErrors.push({engine,cause:event.message,at_ms:epochMain()});
      resolveMessage(engine+'-ready',{kind:'failed',error:event.message});
      browserAbort({code:'PLAYER_WORKER_ERROR',engine});
    };
  }
  return {players:[...playerSlots.keys()],separate_Workers:true};
}
async function loadEarly() {
  const rows=[];
  for(const engine of ['candidate','reference']) {
    const result=waitingMessage(engine+'-ready');slotFor(engine).worker.postMessage({kind:'load',engine});
    const reply=await result;
    if(reply.kind!=='ready')throw Error('PLAYER_LOAD_'+engine+'_'+reply.error);
    rows.push({...reply,engine});
  }
  return {kind:'ready',threads:1,proxy:false,handles:0,activeNN:0,players:rows};
}
function pingEarly(engine='candidate') {const result=waitingMessage(engine+'-ping');slotFor(engine).worker.postMessage({kind:'ping',engine,id:1});return result;}
function startupRootEarly(engine,fixture) {const result=waitingMessage(engine+'-startup-root');slotFor(engine).worker.postMessage({kind:'startup_root',engine,fixture});return result;}
async function dropEarly() {
  await settlePlayerSearches();
  const rows=[];
  for(const engine of ['candidate','reference']) {
    const result=waitingMessage(engine+'-dropped');slotFor(engine).worker.postMessage({kind:'drop',engine});
    const reply=await result;if(reply.handles||reply.activeNN)throw Error('PLAYER_DROP_NOT_ZERO');rows.push(reply);
  }
  return {players:rows,handles:0,activeNN:0};
}
function terminateEarly() {for(const slot of playerSlots.values())slot.worker.terminate();return {players:2,forced:true,at_ms:epochMain()};}
async function calibratePlayerClocks() {
  const clocks={};
  for(const engine of ['candidate','reference']) {
    const samples=[];
    for(let index=0;index<8;index++) {const start=epochMain(),reply=await pingEarly(engine),end=epochMain();samples.push({start_ms:start,end_ms:end,worker_ms:reply.at_ms});}
    const lo=Math.max(...samples.map(row=>row.worker_ms-row.end_ms-.1));
    const hi=Math.min(...samples.map(row=>row.worker_ms-row.start_ms+.1));
    if(lo>hi)throw Error('PLAYER_CLOCK_DISJOINT');
    const clock={lo_ms:lo,hi_ms:hi,mid_ms:(lo+hi)/2,error_ms:(hi-lo)/2+.1,measured:true,samples};
    slotFor(engine).clock=clock;clocks[engine]=clock;
  }
  return clocks;
}

async function browserPreflight() {
  const capabilities={secure:isSecureContext,isolated:crossOriginIsolated,SAB:typeof SharedArrayBuffer,Atomics:typeof Atomics};
  if(!capabilities.secure||!capabilities.isolated||capabilities.SAB!=='function')throw Error('SAB_BROWSER_UNAVAILABLE');
  const state=fromPrefix([]),legal=state.getLegalActions().map(action=>rustAction(state,action));
  const context={generation:1,key:state._positionKey(),legalActions:legal};
  const memory=SharedBestAction.create(context),writer=SharedBestAction.bind(memory,context,context),reader=SharedBestAction.bind(memory,context,context);
  if(reader.readLatest()!==null)throw Error('INITIAL_NOT_NULL');
  writer.publish({completed:true,sequence:1,action:legal[0],value:0,visits:1});
  if(reader.readLatest().action!==legal[0])throw Error('SAB_READ');
  Atomics.store(new Int32Array(memory),SharedBestAction.INDEX.revision,3);
  if(reader.readLatest().sequence!==1)throw Error('BOUNDED_CACHE');
  writer.stop('cancel');
  if(reader.readLatest()!==null)throw Error('CANCEL_NOT_NULL');
  let current=state;
  for(let i=0;i<4;i++) current=current.next(current.getLegalActions()[0]);
  const goal1=new State({boardsize:9,player1pos:[4,8],player2pos:[4,7]});
  const goal2=new State({boardsize:9,player1pos:[4,1],player2pos:[4,0]});
  if(terminalResult(goal1).winner!==1||terminalResult(goal2).winner!==2)throw Error('GOAL_JUDGE');
  const protocolWorker=new Worker('/protocol-worker.js');
  const exchange=(data)=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('PROTOCOL_WORKER_TIMEOUT')),2000);
    protocolWorker.onmessage=event=>{clearTimeout(timer);resolve(event.data);};
    protocolWorker.onerror=event=>{clearTimeout(timer);reject(Error(event.message));};
    protocolWorker.postMessage(data);
  });
  const realMemory=SharedBestAction.create(context);
  const realReader=SharedBestAction.bind(realMemory,context,context);
  const workerCases=[];
  try {
    const attached=await exchange({kind:'attach',memory:realMemory,context,expected:context});
    if(attached.kind!=='attached'||!attached.isolated||!attached.secure)throw Error('WORKER_ISOLATION');
    if(realReader.readLatest()!==null)throw Error('WORKER_FIRST_NONE');
    await exchange({kind:'publish',cp:{completed:true,sequence:1,action:legal[0],value:0.5,visits:1}});
    if(realReader.readLatest()?.action!==legal[0])throw Error('WORKER_SHARED_UPDATE');workerCases.push('cross_worker_complete');
    const incomplete=await exchange({kind:'publish',cp:{completed:false,sequence:2,action:legal[0],value:0.5,visits:1}});
    if(incomplete.kind!=='rejected')throw Error('WORKER_INCOMPLETE');workerCases.push('incomplete_rejected');
    await exchange({kind:'stop',reason:'budget'});
    if(realReader.readLatest()?.sequence!==1)throw Error('WORKER_BUDGET_KEEP');workerCases.push('budget_keeps_complete');
    await exchange({kind:'stop',reason:'cancel'});
    if(realReader.readLatest()!==null)throw Error('WORKER_CANCEL');workerCases.push('cancel_invalidates');
    const foreign=await exchange({kind:'attach',memory:realMemory,context:{...context,key:'foreign'},expected:context});
    if(foreign.kind!=='rejected')throw Error('WORKER_FOREIGN');workerCases.push('foreign_context_rejected');
    const stale=await exchange({kind:'attach',memory:realMemory,context:{...context,generation:2},expected:{...context,generation:2}});
    if(stale.kind!=='rejected')throw Error('WORKER_STALE');workerCases.push('old_generation_rejected');
  } finally { protocolWorker.terminate(); }
  const workerPing=await pingEarly();
  const wasmBytes=await(await fetch('/b.wasm')).arrayBuffer();
  const wasmValid=WebAssembly.validate(wasmBytes);
  if(!wasmValid||workerPing.kind!=='ping')throw Error('DEPENDENCY_PREFLIGHT');
  return {capabilities,initial_null:true,completion:true,bounded_cached:true,cancel_null:true,legal_mock_4ply:current.depth,goal_NN0:2,Worker_SAB_cases:workerCases,original_worker_imports:true,wasm_bytes:wasmBytes.byteLength,wasm_valid:true,Node_judge_calls:0};
}

async function browserStartup(fixtures, references) {
  const clocks=await calibratePlayerClocks();
  const rows=[];startupRows=rows;
  for(const engine of ['candidate','reference'])for(const id of ['initial-p1','asym-hv-p2','straight-jump-p2']) {
    const fixture=fixtures.find(row=>row.id===id),reply=await startupRootEarly(engine,fixture);
    if(reply.kind!=='startup_root'||reply.handles||reply.activeNN||reply.live_searches||reply.active)throw Error('STARTUP_NOT_ZERO');
    BrowserNumeric.check({engine,state:referenceState(fixture),numeric:reply.row,cp:null,reference:references.find(row=>row.id===id)});
    rows.push({engine,id,NN:1,zero:true});
  }
  return {ready:true,startup_NN:6,rows,worker_clocks:clocks,model_sessions:2,tree_history_cache_reused:false};
}

function immutable(value) {
  if(value && typeof value==='object') {
    Object.values(value).forEach(immutable);
    Object.freeze(value);
  }
  return value;
}

function rustPrefix(prefix) {
  let state=fromPrefix([]);
  const ids=[];
  for(const action of prefix) { ids.push(rustAction(state,action));state=state.next(action); }
  return ids;
}

function responseCauses(response, fault) {
  return {
    cancelled:!!response.cancelled,
    browser_late:!!response.late,
    browser_judge:!!response.judge_error,
    external_abort:!!response.external_abort,
    shared_fault:response.shared_state===SharedBestAction.STATE.FAULT,
    received_engine_fault:!!fault && fault.error!=='guard',
    received_fault:fault??null,
    initial_none:!response.completed,
  };
}

function classifyResponse(response, fault) {
  const causes=responseCauses(response,fault);
  // Keep all flags; framework/cancel causes cannot be overwritten by shared FAULT.
  if(causes.external_abort) return 'external_automation_failure';
  if(causes.cancelled) return 'cancel_null';
  if(causes.browser_late) return 'browser_deadline_processing_late';
  if(causes.browser_judge) return 'browser_judge_failure';
  if(causes.received_engine_fault) return 'engine_fault';
  if(causes.shared_fault) return 'ambiguous_shared_fault';
  if(causes.initial_none) return 'initial_no_completed_cp';
  return 'completed_legal';
}

function gameFailureResult(classification, currentPlayer, engine) {
  if(['initial_no_completed_cp','engine_fault'].includes(classification)) return {status:'responsibility_loss',winner:3-currentPlayer,reason:classification,responsible_engine:engine};
  return {status:'unfinished',winner:null,reason:classification};
}

function browserRulesMock() {
  const cases=[];
  for(const [classification,status] of [['initial_no_completed_cp','responsibility_loss'],['engine_fault','responsibility_loss'],['browser_deadline_processing_late','unfinished'],['browser_judge_failure','unfinished'],['external_automation_failure','unfinished']]) {
    const result=gameFailureResult(classification,1,'candidate');
    if(result.status!==status||(status==='unfinished'&&result.winner!==null))throw Error('GAME_FAILURE_CLASSIFICATION');
    cases.push({classification,result});
  }
  if(classifyResponse({late:true},null)!=='browser_deadline_processing_late')throw Error('LATE_CLASSIFICATION');
  if(classifyResponse({judge_error:'SAB_CORRUPT'},null)!=='browser_judge_failure')throw Error('JUDGE_CLASSIFICATION');
  const drawn=new State({boardsize:9,depth:200});
  if(terminalResult(drawn).winner!==0)throw Error('RuleA_DRAW');
  return {cases,RuleA_200_NN0:true,scope:'synthetic classifier/terminal cases; no legal 200ply reachability claim'};
}

async function chooseBrowser(spec, inputState, prefix, reference, config) {
  if(externalAbort)throw Error('EXTERNAL_ABORT_'+externalAbort.code);
  const slot=slotFor(spec.engine);
  const ownWaitStart=epochMain();
  await slot.cleanup;
  const ownWaitEnd=epochMain();
  if(slot.busy || slot.lastACK && (slot.lastACK.handles || slot.lastACK.activeNN || slot.lastACK.live_searches))throw Error('OWN_PLAYER_NOT_REAPED');
  const workerClock=slot.clock;
  const explorationWorker=slot.worker;
  if(Date.now()>=Date.parse(config.processing_deadline))throw Error('PROCESSING_DEADLINE');
  const t0=epochMain();
  const state=inputState ?? fromPrefix(prefix);
  const generation=++generationCounter;
  const requestId=config.run_id+'-'+generation;
  const actions=state.getLegalActions();
  const legal=actions.map(action=>rustAction(state,action));
  const key=state._positionKey();
  const context=immutable({generation,key,legalActions:legal});
  const memory=SharedBestAction.create(context);
  const reader=SharedBestAction.bind(memory,context,context);
  const controlMemory=PlayerControl.create(generation);
  const control=PlayerControl.bind(controlMemory,generation);
  slot.reader=reader;slot.control=control;slot.current=generation;slot.busy=true;
  currentReader=reader;currentGeneration=generation;
  const identity=immutable({engine:spec.engine,request_id:requestId,generation,epoch:generation,fixture:null,legal_prefix:structuredClone(prefix),prefix:rustPrefix(prefix),key,
    history:Array.from(state.position_history).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0),
    model:'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d',schema:'8x9x9-f32/136logits/value1/rust209',
    limits:{simulations:spec.engine==='reference'?100000:4096,max_nodes:spec.engine==='reference'?null:512,max_depth:spec.engine==='reference'?null:24,seed:1979},
    t0_ms:t0,deadline_ms:t0+500,seal_ms:t0+config.adopt_ms,commit_cutoff_ms:t0+402,request_token:requestId});
  const stopPromise=waitingMessage('stop-'+requestId);
  // Observe bounded samples to retain a coherent previous completion; no lock wait.
  let readFault=null;
  let readSamples=0;
  const sampleTimer=setInterval(()=>{
    try { reader.readLatest();readSamples++; } catch(error) { readFault=error.message;reader.stop('fault'); }
  },config.sample_interval_ms);
  pendingTimers.add(sampleTimer);
  let nextState=state;
  const publicPromise=new Promise((resolve,reject)=>{
    const adoptTimer=setTimeout(()=>{
      pendingTimers.delete(adoptTimer);
      clearInterval(sampleTimer);pendingTimers.delete(sampleTimer);
      try {
        const timerAt=epochMain();
        if(spec.cancel||externalAbort)reader.stop('cancel');
        const checkpoint=reader.readLatest();
        let action=null;
        if(checkpoint) {
          const index=legal.indexOf(checkpoint.action);
          if(index<0)throw Error('BROWSER_ILLEGAL_ACTION');
          action=structuredClone(actions[index]);
          // State transition is in main at adoption, before ACK, never in Node.
          nextState=state.next(action);
        }
        control.close(spec.cancel || externalAbort ? 'cancel' : 'adopt');
        reader.stop(spec.cancel || externalAbort ? 'cancel' : 'budget');
        const sharedStatus=reader.status();
        let body={engine:spec.engine,request_id:requestId,generation,action,completed:!!checkpoint,cancelled:!!spec.cancel,sequence:checkpoint?.sequence??null,late:false,judge_error:readFault,shared_state:sharedStatus.state,external_abort:externalAbort};
        let bytes=new TextEncoder().encode(JSON.stringify(body));
        let stamp=epochMain();
        if(stamp>=identity.deadline_ms) {
          body={...body,action:null,completed:false,late:true};
          nextState=state;
          bytes=new TextEncoder().encode(JSON.stringify(body));stamp=epochMain();
        }
        body=immutable(body);
        activeMainState=nextState;
        explorationWorker.postMessage({kind:'cancel',generation:generation+100000});
        let classification=classifyResponse(body,requestFaults.get(requestId));
        const causes=immutable(responseCauses(body,requestFaults.get(requestId)));
        resolve({body,t0_ms:t0,planned_ms:identity.seal_ms,timer_ms:timerAt,stamp_ms:stamp,public_elapsed_ms:stamp-t0,bytes:bytes.length,read_samples:readSamples,body_serialized:JSON.stringify(body),classification,causes,public_did_not_await_ACK:true,Node_clock_referee_calls:0});
      } catch(error) { control.close('abort');reader.stop('fault');explorationWorker.postMessage({kind:'cancel',generation:generation+100000});reject(error); }
    },Math.max(0,identity.seal_ms-epochMain()));
    pendingTimers.add(adoptTimer);
  });
  startedRequests++;
  explorationWorker.postMessage({kind:'request',identity,shared:memory,shared_context:context,control:controlMemory,tail_condition:'cooperative',worker_clock:workerClock,worker_limits:{deadline_ms:t0+500+workerClock.lo_ms,nn_cutoff_ms:t0+402+workerClock.lo_ms},capture_tree:false});
  const response=await publicPromise;
  const row={spec,identity,response,stop:null,gate:null,diagnostic:null,hand_NN:0,Node_per_CP_binding_calls:0};
  collectedRows.push(row); // Keep public even if the later ACK or helper fails.
  row.player_engine=spec.engine;
  row.own_previous_wait={start_ms:ownWaitStart,end_ms:ownWaitEnd,wait_ms:ownWaitEnd-ownWaitStart};
  row.opposite_previous=lastTurnForOther(spec.engine);
  deferredChecks.set(requestId,{state,reference,slot});
  const cleanup=(async()=>{
    const stop=await stopPromise;
    row.stop=stop;row.ACK_wall_ms=stop.main_received_ms-t0;row.worker_clock=workerClock;
    row.worker_stop_interval_main=Number.isFinite(stop.stop.at_ms)?{lower_ms:stop.stop.at_ms-workerClock.hi_ms,upper_ms:stop.stop.at_ms-workerClock.lo_ms}:null;
    row.worker_stop_class=!row.worker_stop_interval_main?'missing':row.worker_stop_interval_main.upper_ms<=identity.deadline_ms?'upper_le_D':row.worker_stop_interval_main.lower_ms>identity.deadline_ms?'lower_gt_D':'straddles_D';
    row.stop_to_main_ACK_interval=row.worker_stop_interval_main?{lower_ms:stop.main_received_ms-row.worker_stop_interval_main.upper_ms,upper_ms:stop.main_received_ms-row.worker_stop_interval_main.lower_ms}:null;
    if(stop.stop.handles||stop.stop.activeNN||stop.stop.live_searches||stop.stop.active)throw Error('OWNED_NOT_ZERO');
    slot.lastACK=stop.stop;slot.busy=false;slot.reader=null;slot.control=null;slot.current=null;
  })();
  slot.cleanup=cleanup;
  pendingCleanups.add(cleanup);
  cleanup.then(()=>pendingCleanups.delete(cleanup),error=>{
    playerErrors.push({request_id:requestId,engine:spec.engine,cause:error.message});
    pendingCleanups.delete(cleanup);browserAbort({code:'OWN_PLAYER_CLEANUP_FAILED',engine:spec.engine});
  });
  currentReader=null;currentGeneration=null;
  return {row,nextState}; // Opposite Worker can receive the new position now.
}

function lastTurnForOther(engine) {
  const row=collectedRows.slice(0,-1).reverse().find(row=>row.spec.engine!==engine);
  return row ? {request_id:row.identity.request_id,public_ms:row.response.stamp_ms,ACK_known_at_next_input:!!row.stop,ACK_ms:row.stop?.main_received_ms??null} : null;
}
async function settlePlayerSearches() {
  const results=await Promise.allSettled([...playerSlots.values()].map(slot=>slot.cleanup));
  const failed=results.find(row=>row.status==='rejected');if(failed)throw failed.reason;
}
async function validateAfterProgression() {
  await settlePlayerSearches();
  for(const row of collectedRows) {
    if(row.diagnostic)continue;
    const {state,reference,slot}=deferredChecks.get(row.identity.request_id);
    const reply=waitingMessage('private-'+row.identity.request_id);
    slot.worker.postMessage({kind:'get_private',request_id:row.identity.request_id});
    const diagnostic=await reply;row.diagnostic=diagnostic;
    row.hand_NN=diagnostic.NN_control_events?.length??diagnostic.NN?.length??0;
    const NN=diagnostic.NN_control_events??diagnostic.NN??[];
    const clock=row.worker_clock;
    row.post_public_NN_definite=NN.filter(span=>span.session_run_start_ms-clock.hi_ms>row.response.stamp_ms).length;
    row.post_cutoff_NN_definite=NN.filter(span=>span.session_run_start_ms-clock.hi_ms>row.identity.commit_cutoff_ms).length;
    row.post_cutoff_NN_possible=NN.filter(span=>span.session_run_start_ms-clock.lo_ms>row.identity.commit_cutoff_ms).length;
    row.NN_returned_after_public=NN.filter(span=>span.return_ms-clock.hi_ms>row.response.stamp_ms).length;
    if(!diagnostic?.numeric?.length)throw Error('ROOT_NUMERIC_MISSING');
    row.gate=BrowserNumeric.check({engine:row.spec.engine,state,numeric:diagnostic.numeric[0],cp:diagnostic.validated_cp,reference});
    row.postpublic_immutable=JSON.stringify(row.response.body)===row.response.body_serialized;
    if(!row.postpublic_immutable)throw Error('POST_PUBLIC_MUTATION');
  }
  for(const row of collectedRows) {
    if(!row.opposite_previous)continue;
    const previous=collectedRows.find(r=>r.identity.request_id===row.opposite_previous.request_id);
    row.opposite_previous.final_ACK_ms=previous.stop?.main_received_ms??null;
    row.opposite_previous.input_before_old_ACK=!!previous.stop&&row.identity.t0_ms<previous.stop.main_received_ms;
    row.opposite_previous.residual_overlap_wall_ms=previous.stop?Math.max(0,previous.stop.main_received_ms-row.identity.t0_ms):null;
  }
}

async function runFunctional(config, references) {
  for(const spec of config.schedule) {
    await chooseBrowser(spec,fromPrefix([]),[],references.find(row=>row.id==='initial-p1'),config);
  }
  let state=fromPrefix([]),prefix=[];
  for(let ply=0;ply<(config.dynamic_plies??0);ply++) {
    const engine=state.getCurrentPlayer()===1?'candidate':'reference';
    const {row,nextState}=await chooseBrowser({engine,cancel:false,dynamic_ply:ply},state,prefix,prefix.length?null:references.find(row=>row.id==='initial-p1'),config);
    if(!row.response.body.completed)break;
    prefix.push(structuredClone(row.response.body.action));state=nextState;
  }
  await validateAfterProgression();
  return {rows:collectedRows,dynamic:{plies:prefix.length,prefix,terminal:terminalResult(state)},started_requests:startedRequests,game_starts:0};
}

function collectBrowser() {
  return {rows:collectedRows,games:collectedGames,startup_rows:startupRows,started_requests:startedRequests,started_games:startedGames,waiting_messages:[...waitingMessages.keys()],main_timer_count:pendingTimers.size,external_abort:externalAbort,player_errors:playerErrors,player_status:[...playerSlots.values()].map(slot=>({engine:slot.engine,busy:slot.busy,last_ACK:slot.lastACK}))};
}

function browserAbort(reason) {
  externalAbort=reason;
  for(const slot of playerSlots.values()) {
    slot.control?.close('abort');slot.reader?.stop('cancel');
    if(slot.current!==null)slot.worker.postMessage({kind:'cancel',generation:slot.current+100000,engine:slot.engine});
  }
  return {cause:reason,at_ms:epochMain(),fresh_forbidden:true};
}

async function runBrowserGames(config, fixtures, references) {
  for(const planned of config.games) {
    if(externalAbort||Date.now()>=Date.parse(config.processing_deadline))break;
    const fixture=fixtures.find(row=>row.id===planned.fixture_id);
    const prefix=structuredClone(fixture.legal_prefix);
    let state=referenceState(fixture);
    const game={id:planned.id,fixture_id:fixture.id,candidate_color:planned.candidate_color,seed:1979,status:'started',initial_prefix:structuredClone(prefix),actions:[],turn_indices:[],winner:null,reason:null};
    collectedGames.push(game);startedGames++;
    try {
      while(!terminalResult(state)) {
        if(externalAbort){game.status='unfinished';game.reason=externalAbort.code;break;}
        const engine=state.getCurrentPlayer()===planned.candidate_color?'candidate':'reference';
        const rootReference=prefix.length===fixture.legal_prefix.length?references.find(row=>row.id===fixture.id):null;
        const {row,nextState}=await chooseBrowser({engine,cancel:false,game_id:game.id,turn:game.actions.length},state,prefix,rootReference,config);
        game.turn_indices.push(row.identity.request_id);
        const failure=row.response.classification;
        if(failure!=='completed_legal') {
          Object.assign(game,gameFailureResult(failure,state.getCurrentPlayer(),engine));
          break;
        }
        const action=structuredClone(row.response.body.action);
        game.actions.push(action);prefix.push(action);state=nextState;
      }
      const terminal=terminalResult(state);
      if(terminal){game.status='terminal';game.winner=terminal.winner;game.reason=terminal.winner?'goal':'RuleA_draw';}
      game.final_key=state._positionKey();game.total_ply=state.depth;
    }catch(error){game.status='unfinished';game.reason='browser_infrastructure_failure';game.error={name:error.name,message:error.message};throw error;}
    await settlePlayerSearches();
    if(game.status==='unfinished')break;
  }
  await validateAfterProgression();
  return collectBrowser();
}

function abortBrowserTimers() {
  for(const timer of pendingTimers){clearTimeout(timer);clearInterval(timer);}
  pendingTimers.clear();
  return {main_timers:0,pending_messages:[...waitingMessages.keys()]};
}

async function playerRoutingMock() {
  const context={generation:900001,key:'player-mock',legalActions:[13]};
  const memory=SharedBestAction.create(context);
  const writer=SharedBestAction.bind(memory,context,context);
  const reader=SharedBestAction.bind(memory,context,context);
  const control=PlayerControl.bind(PlayerControl.create(context.generation),context.generation);
  if(reader.readLatest()!==null)throw Error('MOCK_FIRST_NONE');
  writer.publish({completed:true,sequence:1,action:13,value:.2,visits:1});
  const adopted=reader.readLatest();
  control.close('adopt');reader.stop('budget');
  if(control.active()||writer.publish({completed:true,sequence:2,action:13,value:.3,visits:2}))throw Error('POST_ADOPT_UPDATE');
  if(reader.readLatest().sequence!==1||adopted.sequence!==1)throw Error('ADOPTED_MUTATION');
  let oldACK=false;
  const old=new Promise(resolve=>setTimeout(()=>{oldACK=true;resolve();},25));
  // The same engine-slot cleanup promise used by chooseBrowser; only the own
  // slot must settle. Opposite dispatch never awaits the old slot.
  const candidate=slotFor('candidate'),reference=slotFor('reference');
  candidate.cleanup=old;
  await reference.cleanup;
  const oppositeBeforeACK=!oldACK;
  await candidate.cleanup;
  if(!oppositeBeforeACK||!oldACK||candidate.worker===reference.worker)throw Error('PLAYER_SLOT_ISOLATION');
  reader.stop('cancel');
  if(reader.readLatest()!==null)throw Error('CANCEL_REUSE');
  try { PlayerControl.bind(control.words.buffer,context.generation+1);throw Error('OLD_GENERATION_ACCEPTED'); }
  catch(error) { if(error.message!=='CONTROL_GENERATION')throw error; }
  return {players:2,first_none:true,adopted_immutable:true,post_adopt_new_NN_disabled:true,
    opposite_before_old_ACK:oppositeBeforeACK,own_before_restart_waited:true,cancel_reuse:false,
    old_generation_rejected:true,model_NN:0,scope:'mock delay, not CPU or browser timer guarantee'};
}
