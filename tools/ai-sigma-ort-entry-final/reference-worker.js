'use strict';
// ============================================================
// mcts_worker.js — Web Worker: MCTS engine + ONNX Runtime Web
// ============================================================

// Load game engine and ORT at TOP LEVEL (synchronous) so they are
// guaranteed available before any async code or message handling.
// Both files are same-origin to avoid CORS / COEP issues in the Worker.
importScripts('game.js');
importScripts('ort.min.js');
importScripts('context.js');   // local copy of onnxruntime-web

// ── ONNX Runtime Web ────────────────────────────────────────────────────────
let ortSession = null;
let _activeTaskGen = -1;  // incremented on each new task; used to cancel stale loops
const DEFAULT_MODEL_PATH = './models/supervised_extended.onnx';
const START_MODEL_PATH = (() => {
  try { return new URL(self.location.href).searchParams.get('model') || DEFAULT_MODEL_PATH; }
  catch (_) { return DEFAULT_MODEL_PATH; }
})();

// Whether the loaded net is "full-canonical" (trained after the 2026-07-19
// policy-frame fix). Only those need P2's policy un-flipped; pre-fix
// "half-canonical" nets (all 7x7 models, and the retired 9x9 legacy
// checkpoints) output P2 policy already in the real-board frame and must NOT
// be un-flipped. The ONNX can't self-describe this, so we key on the model
// directory: the active 9x9 lineage (models_9x9/) is full-canonical, and the
// half-canonical 9x9 legacy checkpoints have been removed from the picker.
function isFullCanonicalModel(path) {
  return /models_9x9\b/.test(path || '');
}
let modelFullCanonical = isFullCanonicalModel(START_MODEL_PATH);

// Configure ORT immediately after importScripts while ort is guaranteed defined.
try {
  // WASM binaries are fetched from the CDN; credentials are not needed.
  ort.env.wasm.wasmPaths = new URL('/ort/',self.location.href).href;
  // Multi-threaded WASM (intra-op parallelism for the conv/matmul work in
  // each inference call) needs SharedArrayBuffer, which needs cross-origin
  // isolation — already set up via COOP/COEP (serve.py locally,
  // coi-serviceworker.js on GitHub Pages), so this is safe to enable. Falls
  // back to single-threaded automatically if crossOriginIsolated is false
  // for any reason. Capped rather than using the full core count to avoid
  // hogging low-end visitor machines.
  ort.env.wasm.numThreads = 1;
  // We are already inside a Worker — do not proxy back to main thread.
  ort.env.wasm.proxy = false;
} catch (e) {
  console.error('[worker] ORT env setup failed:', e);
}

(async function loadONNX() {
  try {
    // Force the WASM execution provider so WebGPU/WebGL detection is skipped.
    ortSession = await ort.InferenceSession.create(START_MODEL_PATH, {
      executionProviders: ['wasm'],
    });
    console.log('[worker] ONNX model loaded OK');
    postMessage({type:'model_loaded',version:ort.env.versions,threads:ort.env.wasm.numThreads,proxy:ort.env.wasm.proxy,canonical:modelFullCanonical,inputs:ortSession.inputNames,outputs:ortSession.outputNames});
  } catch (e) {
    console.error('[worker] ONNX model load failed:', e);
    postMessage({ type: 'model_failed', reason: String(e.message || e) });
  }
})();

// NOTE: actionLabel() / PAWN_ARROW now live in game.js (imported above) so the
// main thread can label timeline plies with the same strings used here.

// ── Evaluators ───────────────────────────────────────────────────────────────
const stamp=()=>performance.timeOrigin+performance.now();
let clockContext=null;
function check(c,heavy=false){if(!c)return;if(c.generation!==_activeTaskGen)throw Error('cancelled');if(stamp()>=(heavy?c.stop:c.deadline))throw Error(heavy?'guard':'deadline');}
async function rawNN(state){
 const c=clockContext;check(c,true);if(!ortSession)throw Error('model_not_ready');
 const features=state.toNNInput();if(features.length!==648||features.some(x=>!Number.isFinite(x)))throw Error('feature_shape_finite');
 const tensor=new ort.Tensor('float32',features,[1,8,9,9]);let res;const start=stamp();
 if(c){c.nnCalls++;if(c.notify&&!c.notified){c.notified=true;postMessage({type:'nn_started',generation:c.generation,at:start});}}
 try{res=await ortSession.run({input:tensor});const end=stamp();if(c)c.nn.push({start,end});check(c);
  if(JSON.stringify(res.policy_logits.dims)!=='[1,136]'||JSON.stringify(res.value.dims)!=='[1,1]')throw Error('output_shape');
  const logits=Array.from(res.policy_logits.data),value=res.value.data[0];if(logits.some(x=>!Number.isFinite(x))||!Number.isFinite(value)||Math.abs(value)>1)throw Error('output_finite_value');
  return {features:Array.from(features),policy_logits:logits,value,shapes:[res.policy_logits.dims,res.value.dims]};
 }finally{tensor.dispose?.();if(res)for(const x of Object.values(res))x.dispose?.();}
}
function legalPriors(state,legal,logits){const flip=modelFullCanonical&&!state.isPlayer1Turn(),perm=flip?vertPolicyPermutation(9):null;const indices=legal.map(a=>{let i=actionToIndex(a,9);return flip?perm[i]:i;});const max=Math.max(...indices.map(i=>logits[i]));const exps=indices.map(i=>Math.exp(logits[i]-max)),sum=exps.reduce((a,b)=>a+b,0);return {indices,priors:exps.map(x=>x/sum)};}
async function nnEvaluator(state,legal){if(!legal.length)throw Error('nn_empty_legal');const r=await rawNN(state);return [legalPriors(state,legal,r.policy_logits).priors,r.value];}

function rolloutEvaluator(state, legalActions) {
  const n      = legalActions.length;
  const priors = n > 0 ? new Array(n).fill(1 / n) : [];
  const value  = n > 0 ? randomRollout(state) : 0;
  return [priors, value];
}

function randomRollout(rootState) {
  const rootPlayer = rootState.getCurrentPlayer();
  let s = rootState, steps = 0;
  while (!s.isFinished() && steps < 300) {
    const acts = s.getLegalActions();
    if (acts.length === 0) break;
    s = s.next(acts[Math.floor(Math.random() * acts.length)]);
    steps++;
  }
  const w = s.winner();
  if (w === 0) return 0;
  return w === rootPlayer ? 1 : -1;
}

// ── Minimax ─────────────────────────────────────────────────────────────────
function minimaxHeuristic(state, maximizingPlayer) {
  const N = state.boardsize;
  const [p1x, p1y] = state.player1pos;
  const [p2x, p2y] = state.player2pos;
  const p1Dist = state.p1_dist[p1y * N + p1x];
  const p2Dist = state.p2_dist[p2y * N + p2x];
  return maximizingPlayer === 1 ? p2Dist - p1Dist : p1Dist - p2Dist;
}

function minimaxTerminalValue(state, maximizingPlayer) {
  const winner = state.winner();
  if (winner === maximizingPlayer) return 1e9;
  if (winner !== 0) return -1e9;
  if (state.isDrawn()) return 0;
  return null;
}

function orderedMinimaxActions(state) {
  const legal = state.getLegalActions();
  const advantages = state.computeMoveAdvantages(legal);
  return legal
    .map((action, i) => ({ action, advantage: advantages[i] }))
    .sort((a, b) => b.advantage - a.advantage)
    .map(item => item.action);
}

function alphabeta(state, depth, alpha, beta, maximizing, maximizingPlayer) {
  const terminal = minimaxTerminalValue(state, maximizingPlayer);
  if (terminal !== null) return terminal;
  if (depth === 0) return minimaxHeuristic(state, maximizingPlayer);

  const legal = orderedMinimaxActions(state);
  if (legal.length === 0) return minimaxHeuristic(state, maximizingPlayer);

  if (maximizing) {
    let value = -1e18;
    for (const action of legal) {
      value = Math.max(value, alphabeta(state.next(action), depth - 1, alpha, beta, false, maximizingPlayer));
      alpha = Math.max(alpha, value);
      if (alpha >= beta) break;
    }
    return value;
  }

  let value = 1e18;
  for (const action of legal) {
    value = Math.min(value, alphabeta(state.next(action), depth - 1, alpha, beta, true, maximizingPlayer));
    beta = Math.min(beta, value);
    if (alpha >= beta) break;
  }
  return value;
}

function selectMinimaxAction(state, depth) {
  const maximizingPlayer = state.getCurrentPlayer();
  const legal = orderedMinimaxActions(state);
  let bestValue = -1e18;
  let bestActions = [];
  for (const action of legal) {
    const value = alphabeta(state.next(action), depth - 1, bestValue, 1e18, false, maximizingPlayer);
    if (value > bestValue) {
      bestValue = value;
      bestActions = [action];
    } else if (value === bestValue) {
      bestActions.push(action);
    }
  }
  return bestActions.length ? bestActions[Math.floor(Math.random() * bestActions.length)] : null;
}

// ── MCTS ──────────────────────────────────────────────────────────────────────
class MCTSNode {
  constructor(state, parent = null, action = null, prior = 1.0, parentState = null) {
    this.state        = state;
    this._parentState = parentState;
    this.parent       = parent;
    this.action       = action;
    this.prior        = prior;
    this.basePrior    = prior;
    this.children     = [];
    this.visitCount   = 0;
    this.valueSum     = 0;
    this.isExpanded   = false;
  }

  ensureState() {
    if (this.state === null) {
      this.state        = this._parentState.next(this.action);
      this._parentState = null;
    }
  }

  get qValue() { return this.visitCount === 0 ? 0 : this.valueSum / this.visitCount; }

  bestChild(cPuct = 1.0, fpuReduction = 0.2) {
    const pq      = this.qValue;
    const sqrtN   = Math.sqrt(this.visitCount);
    let visitedPriorSum = 0;
    for (const c of this.children) if (c.visitCount > 0) visitedPriorSum += c.basePrior;
    let best = null, bestScore = -Infinity;
    for (const c of this.children) {
      const u     = cPuct * c.prior * sqrtN / (1 + c.visitCount);
      const q     = c.visitCount === 0
        ? pq - fpuReduction * Math.sqrt(visitedPriorSum)
        : -c.qValue;
      const score = q + u;
      if (score > bestScore) { bestScore = score; best = c; }
    }
    return best;
  }
}

const C_PUCT       = 1.0;
const FPU_REDUCTION = 0.2;

async function expandNode(node, evaluator) {
  const legal = node.state.getLegalActions();
  let priors, value;
  if (legal.length === 0) {
    priors = []; value = 0;
  } else {
    [priors, value] = await evaluator(node.state, legal);
  }
  for (let i = 0; i < legal.length; i++) {
    node.children.push(new MCTSNode(null, node, legal[i], priors[i], node.state));
  }
  node.isExpanded = true;
  return value;
}

function backup(node, value) {
  let n = node;
  while (n !== null) { n.visitCount++; n.valueSum += value; value = -value; n = n.parent; }
}

function selectLeaf(root) {
  let node = root;
  while (true) {
    node.ensureState();
    if (!node.isExpanded || node.state.isFinished()) break;
    node = node.bestChild(C_PUCT, FPU_REDUCTION);
  }
  return node;
}

async function runMCTS(state,numSims,evaluator,cancelToken,onProgress=null){
 const c=clockContext,root=new MCTSNode(state);let checkpoint=null;
 function commit(){check(c);const p=pickFromVisits(root.children,0);if(p)checkpoint={action:p.action,at:stamp(),rootVisits:root.visitCount,simulations:c.simulations};check(c);c.checkpoint=checkpoint;}
 try{check(c,true);const initVal=await expandNode(root,evaluator);check(c);backup(root,initVal);commit();c.rootFinished=stamp();await new Promise(r=>setTimeout(r,0));
  for(let i=0;i<numSims;i++){check(c,true);const begin=stamp(),leaf=selectLeaf(root);leaf.ensureState();check(c);let value;
   const t=terminalResult(leaf.state);if(t)value=t.value;else value=await expandNode(leaf,evaluator);
   check(c);backup(leaf,value);check(c);c.simulations++;commit();c.steps.push(stamp()-begin);await new Promise(r=>setTimeout(r,0));
  }
 }catch(e){if(e.message!=='guard')throw e;c.stopped='guard';}
 check(c);return root;
}

// Pick a child from the root's visit counts, matching Python
// MCTSAgent.get_policy + select_action (mcts.py): temperature 0 is argmax,
// above 0 samples proportional to visitCount^(1/T).
function pickFromVisits(children, temperature) {
  if (!children.length) return null;
  let best = children[0];
  for (const c of children) if (c.visitCount > best.visitCount) best = c;
  if (!(temperature > 0)) return best;
  const maxN = best.visitCount;
  if (maxN <= 0) return children[Math.floor(Math.random() * children.length)];

  // Dividing by maxN cancels in the normalisation below, but keeps
  // visitCount^(1/T) from overflowing to Infinity at low T (5000^100 does).
  const invT  = 1 / temperature;
  const raw   = children.map(c => Math.pow(c.visitCount / maxN, invT));
  const total = raw.reduce((s, r) => s + r, 0);
  if (!(total > 0)) return best;
  let r = Math.random() * total;
  for (let i = 0; i < children.length; i++) {
    r -= raw[i];
    if (r <= 0) return children[i];
  }
  return best;   // only reachable through float drift
}

async function selectAction(state, numSims, evaluator, cancelToken, onProgress = null,
                            temperature = 0) {
  const root = await runMCTS(state, numSims, evaluator, cancelToken, onProgress);
  if (!root) return null;
  const pick = pickFromVisits(root.children, temperature);
  return pick ? pick.action : (state.getLegalActions()[0] || null);
}

async function getPolicy(state, numSims, evaluator, cancelToken, onProgress = null) {
  const root = await runMCTS(state, numSims, evaluator, cancelToken, onProgress);
  if (!root) return null;
  const total = root.children.reduce((s, c) => s + c.visitCount, 0);
  const rootQ = root.qValue;
  const policy = root.children
    .map(c => ({ action: c.action, prob: total > 0 ? c.visitCount / total : 0 }))
    .sort((a, b) => b.prob - a.prob);
  return { policy, rootQ };
}

// ── Reconstruct State from worker-message payload ────────────────────────────
function stateFromMsg(d) {
  return new State({
    boardsize:        d.boardsize,
    depth:            d.depth,
    player1pos:       d.player1pos,
    player2pos:       d.player2pos,
    hwalls:           new Uint8Array(d.hwalls),
    vwalls:           new Uint8Array(d.vwalls),
    walls_p1:         d.walls_p1,
    walls_p2:         d.walls_p2,
    walls_initial:    d.walls_initial,
    hwall_anchors:    new Set(d.hwall_anchors),
    vwall_anchors:    new Set(d.vwall_anchors),
    position_history: new Map(d.position_history),
    // p1_dist etc. not sent — recomputed from walls in constructor
  });
}


let queue=Promise.resolve();
onmessage=e=>{const d=e.data;_activeTaskGen=d.generation;
 if(d.type==='cancel'){postMessage({type:'cancel_ack',generation:d.generation,at:stamp()});return;}
 queue=queue.then(async()=>{let c=null;try{
  if(d.generation!==_activeTaskGen)throw Error('cancelled');
  if(d.type==='fallback_test'){const keep=ortSession;ortSession=null;let error;try{await rawNN(referenceState(d.fixture));}catch(e){error=e.message;}finally{ortSession=keep;}postMessage({type:'response',transaction:{request_id:d.request_id,generation:d.generation,engine:'reference',prefix:d.prefix,legal_prefix:d.legal_prefix,seed:d.seed,simulations:d.simulations,max_nodes:d.max_nodes,max_depth:d.max_depth,T_ms:d.T_ms,g_ms:d.g_ms},generation:d.generation,error,fallback:0});return;}
  if(d.type==='clock_ping'){postMessage({type:'response',transaction:{request_id:d.request_id,generation:d.generation,engine:'reference',prefix:d.prefix,legal_prefix:d.legal_prefix,seed:d.seed,simulations:d.simulations,max_nodes:d.max_nodes,max_depth:d.max_depth,T_ms:d.T_ms,g_ms:d.g_ms},generation:d.generation,clock_ms:stamp()});return;}
  if(d.type==='value_injection'){const original=ortSession.run.bind(ortSession);let error=null;try{ortSession.run=async(...args)=>{const r=await original(...args);r.value.data[0]=d.value;return r;};await rawNN(fromPrefix([]));}catch(e){error=e.message;}finally{ortSession.run=original;}postMessage({type:'response',transaction:{request_id:d.request_id,generation:d.generation,engine:'reference',prefix:d.prefix,legal_prefix:d.legal_prefix,seed:d.seed,simulations:d.simulations,max_nodes:d.max_nodes,max_depth:d.max_depth,T_ms:d.T_ms,g_ms:d.g_ms},generation:d.generation,error,fallback:0});return;}
  if(d.type==='numeric'){clockContext=null;const state=referenceState(d.fixture),r=await rawNN(state),legal=state.getLegalActions(),p=legal.length?legalPriors(state,legal,r.policy_logits):{indices:[],priors:[]};postMessage({type:'response',transaction:{request_id:d.request_id,generation:d.generation,engine:'reference',prefix:d.prefix,legal_prefix:d.legal_prefix,seed:d.seed,simulations:d.simulations,max_nodes:d.max_nodes,max_depth:d.max_depth,T_ms:d.T_ms,g_ms:d.g_ms},generation:d.generation,id:d.fixture.id,...r,...p,terminal:terminalResult(state),fallback:0});return;}
  if(d.type!=='search')throw Error('unsupported_request');
  c={generation:d.generation,t0:d.t0,deadline:d.t0+d.T_ms,stop:d.t0+d.T_ms-d.g_ms,nnCalls:0,nn:[],simulations:0,steps:[],notify:d.notify,workerStart:stamp()};clockContext=c;check(c,true);
  const state=requestState(d),terminal=terminalResult(state);check(c);
  if(!terminal)await runMCTS(state,d.limits.maxSimulations,nnEvaluator,d.generation);
  check(c);const finish=stamp();postMessage({type:'response',transaction:{request_id:d.request_id,generation:d.generation,engine:'reference',prefix:d.prefix,legal_prefix:d.legal_prefix,seed:d.seed,simulations:d.simulations,max_nodes:d.max_nodes,max_depth:d.max_depth,T_ms:d.T_ms,g_ms:d.g_ms},generation:d.generation,id:d.id??d.fixture?.id,terminal,action:terminal?null:c.checkpoint?.action??null,actionRust209:terminal?null:c.checkpoint?rustAction(state,c.checkpoint.action):null,time:{t0:c.t0,workerStart:c.workerStart,rootFinished:c.rootFinished,finish,checkpoint:c.checkpoint?.at},stats:{nnCalls:c.nnCalls,nn:c.nn,simulations:c.simulations,rootVisits:c.checkpoint?.rootVisits??0,steps:c.steps,stopped:c.stopped},modelhash:'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d',fallback:0,error:!terminal&&!c.checkpoint?'no_checkpoint':null});
 }catch(e){postMessage({type:'response',transaction:{request_id:d.request_id,generation:d.generation,engine:'reference',prefix:d.prefix,legal_prefix:d.legal_prefix,seed:d.seed,simulations:d.simulations,max_nodes:d.max_nodes,max_depth:d.max_depth,T_ms:d.T_ms,g_ms:d.g_ms},generation:d.generation,id:d.id??d.fixture?.id,error:String(e.message||e),fallback:0,stats:c?{nnCalls:c.nnCalls,nn:c.nn,simulations:c.simulations,rootVisits:c.checkpoint?.rootVisits??0,steps:c.steps}:null,time:c?{t0:c.t0,workerStart:c.workerStart,finish:stamp(),checkpoint:c.checkpoint?.at}:null});}finally{clockContext=null;}});
};
