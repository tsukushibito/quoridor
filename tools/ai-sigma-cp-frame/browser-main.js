'use strict';
let explorationWorker;
let generationCounter = 0;
const waitingMessages = new Map();
const privateDiagnostics = new Map();
const epochMain = ()=>performance.timeOrigin+performance.now();
function waitingMessage(key) { return new Promise(resolve=>waitingMessages.set(key,resolve)); }
function resolveMessage(key, value) {
  const resolve=waitingMessages.get(key);
  if (resolve) { waitingMessages.delete(key); resolve(value); }
}
function setupEarly() {
  explorationWorker = new Worker('/early-worker.js');
  explorationWorker.onmessage=({data:message})=>{
    if(message.kind==='private_done') privateDiagnostics.set(message.identity.request_id,message);
    else if(message.kind==='stopped') resolveMessage('stop-'+message.identity.request_id,{...message,main_received_ms:epochMain()});
    else if(message.kind==='startup_root') resolveMessage('startup-root',message);
    else if(message.kind==='ready'||message.kind==='failed') resolveMessage('ready',message);
    else if(message.kind==='dropped') resolveMessage('dropped',message);
    else if(message.kind==='ping') resolveMessage('ping',message);
  };
  explorationWorker.onerror=event=>resolveMessage('ready',{kind:'failed',error:event.message});
  return true;
}
function loadEarly(){const result=waitingMessage('ready');explorationWorker.postMessage({kind:'load'});return result;}
function pingEarly(){const result=waitingMessage('ping');explorationWorker.postMessage({kind:'ping',id:1});return result;}
function startupRootEarly(engine,fixture){const result=waitingMessage('startup-root');explorationWorker.postMessage({kind:'startup_root',engine,fixture});return result;}
function dropEarly(){const result=waitingMessage('dropped');explorationWorker.postMessage({kind:'drop'});return result;}
function terminateEarly(){explorationWorker.terminate();return {forced:true,at_ms:epochMain()};}

function browserPreflight() {
  const capabilities={secure:isSecureContext,isolated:crossOriginIsolated,SAB:typeof SharedArrayBuffer,Atomics:typeof Atomics};
  if(!capabilities.secure||!capabilities.isolated||capabilities.SAB!=='function')throw Error('SAB_BROWSER_UNAVAILABLE');
  const state=fromPrefix([]),legal=state.getLegalActions().map(action=>rustAction(state,action));
  const context={generation:1,key:state._positionKey(),legalActions:legal};
  const memory=SharedBestAction.create(context),writer=SharedBestAction.bind(memory,context,context),reader=SharedBestAction.bind(memory,context,context);
  if(reader.readLatest()!==null)throw Error('INITIAL_NOT_NULL');
  writer.publish({completed:true,sequence:1,action:legal[0],value:0,visits:1});
  if(reader.readLatest().action!==legal[0])throw Error('SAB_READ');
  new Int32Array(memory)[SharedBestAction.INDEX.revision]=3;
  if(reader.readLatest().sequence!==1)throw Error('BOUNDED_CACHE');
  writer.stop('cancel');
  if(reader.readLatest()!==null)throw Error('CANCEL_NOT_NULL');
  let current=state;
  for(let i=0;i<4;i++) current=current.next(current.getLegalActions()[0]);
  const goal1=new State({boardsize:9,player1pos:[4,8],player2pos:[4,7]});
  const goal2=new State({boardsize:9,player1pos:[4,1],player2pos:[4,0]});
  if(terminalResult(goal1).winner!==1||terminalResult(goal2).winner!==2)throw Error('GOAL_JUDGE');
  return {capabilities,initial_null:true,completion:true,bounded_cached:true,cancel_null:true,legal_mock_4ply:current.depth,goal_NN0:2,Node_judge_calls:0};
}

async function browserStartup(fixtures, references) {
  const rows=[];
  for(const engine of ['candidate','reference'])for(const id of ['initial-p1','asym-hv-p2','straight-jump-p2']) {
    const fixture=fixtures.find(row=>row.id===id),reply=await startupRootEarly(engine,fixture);
    if(reply.kind!=='startup_root'||reply.handles||reply.activeNN||reply.live_searches||reply.active)throw Error('STARTUP_NOT_ZERO');
    BrowserNumeric.check({engine,state:referenceState(fixture),numeric:reply.row,cp:null,reference:references.find(row=>row.id===id)});
    rows.push({engine,id,NN:1,zero:true});
  }
  return {ready:true,startup_NN:6,rows,tree_history_cache_reused:false};
}

async function browserRequest(spec, reference) {
  const t0=epochMain();
  const state=fromPrefix([]),prefix=[],generation=++generationCounter;
  const legal=state.getLegalActions().map(action=>rustAction(state,action));
  const context={generation,key:state._positionKey(),legalActions:legal};
  const memory=SharedBestAction.create(context),reader=SharedBestAction.bind(memory,context,context);
  const identity={engine:spec.engine,request_id:'sab-'+generation,generation,epoch:generation,fixture:null,legal_prefix:[],prefix:[],key:context.key,history:Array.from(state.position_history).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0),model:'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d',schema:'8x9x9-f32/136logits/value1/rust209',limits:{simulations:spec.engine==='reference'?100000:4096,max_nodes:spec.engine==='reference'?null:512,max_depth:spec.engine==='reference'?null:24,seed:1979},t0_ms:t0,deadline_ms:t0+500,seal_ms:t0+411,commit_cutoff_ms:t0+402,request_token:'sab-'+generation};
  const stopPromise=waitingMessage('stop-'+identity.request_id);
  const decisionPromise=new Promise((resolve,reject)=>setTimeout(()=>{
    try {
    const timerAt=epochMain();
    if(spec.cancel) reader.stop('cancel');
    const cp=reader.readLatest();
    let action=null;
    if(cp) {
      const matches=state.getLegalActions().filter(action=>rustAction(state,action)===cp.action);
      if(matches.length!==1)throw Error('BROWSER_ILLEGAL_ACTION');
      action=structuredClone(matches[0]);
    }
    const body={engine:spec.engine,action,completed:!!cp,sequence:cp?.sequence??null,cancelled:!!spec.cancel};
    const encoded=new TextEncoder().encode(JSON.stringify(body));
    const stamp=epochMain();
    const late=stamp>=identity.deadline_ms;
    const final=late?{...body,action:null,completed:false}:body;
    if(late)new TextEncoder().encode(JSON.stringify(final));
    const finalStamp=epochMain();
    explorationWorker.postMessage({kind:'cancel',generation:generation+100000});
    resolve({body:final,t0,planned_ms:t0+411,timer_ms:timerAt,stamp_ms:finalStamp,late,encoded_bytes:encoded.length,deadline_processing_late:late,Node_clock_referee_calls:0});
    } catch(error) { reader.stop('fault'); explorationWorker.postMessage({kind:'cancel',generation:generation+100000}); reject(error); }
  },Math.max(0,t0+411-epochMain())));
  explorationWorker.postMessage({kind:'request',identity,shared:memory,shared_context:context,tail_condition:'cooperative',worker_limits:{deadline_ms:t0+500,nn_cutoff_ms:t0+402},capture_tree:false});
  const response=await decisionPromise;
  const stop=await stopPromise; // After public; safe next input only.
  if(stop.stop.handles||stop.stop.activeNN||stop.stop.live_searches||stop.stop.active)throw Error('OWNED_NOT_ZERO');
  const diagnostic=privateDiagnostics.get(identity.request_id);
  const gate=BrowserNumeric.check({engine:spec.engine,state,numeric:diagnostic.numeric[0],cp:diagnostic.validated_cp,reference});
  return {spec,response,stop,gate,diagnostic,ACK_wall_ms:stop.main_received_ms-t0,hand_NN:diagnostic.NN.length,per_CP_Node_messages:0};
}
