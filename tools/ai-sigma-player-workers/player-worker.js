'use strict';
importScripts('/shared-best-action.js', '/snapshot-cache.js', '/player-control.js');
const boundEngine = new URL(self.location.href).searchParams.get('engine');
if (!['candidate', 'reference'].includes(boundEngine)) throw Error('PLAYER_ENGINE_BINDING');
const sendDiagnostic = postMessage.bind(globalThis);
let channel = null;
let completeCache = null;
let latestCP = null;
let requestClock = { mid_ms: 0, error_ms: 0 };
let requestControl = null;
let requestIdentity = null;
let publications = [];
let NNcontrolEvents = [];
let discardedSnapshots = 0;
const deferredPrivate = new Map();
const workerNow = () => performance.timeOrigin + performance.now();

function send(message) { sendDiagnostic({ ...message, worker_engine: boundEngine }); }
function retired() { return requestControl && !requestControl.active(); }
function synchronizeRetirement() {
  if (retired() && generation === requestIdentity.generation) generation = requestIdentity.generation + 100000;
  return retired();
}

globalThis.postMessage = function(message) {
  if (message.kind === 'snapshot') {
    if (retired()) { discardedSnapshots++; synchronizeRetirement(); return; }
    const begin = workerNow();
    const cacheMessage = { ...message, sent_ms: message.sent_ms - requestClock.mid_ms,
      owned: { ...message.owned, completed_at: message.owned.completed_at - requestClock.mid_ms } };
    if (completeCache.receive(cacheMessage)) {
      const cp = completeCache.cache.owned.cp;
      if (channel.publish({ completed: true, sequence: message.sequence, action: cp.action,
        value: message.value, visits: cp.simulations })) {
        latestCP = cp;
        publications.push({ sequence: message.sequence, action: cp.action, begin_ms: begin, validation_end_ms: workerNow() });
      }
    }
    return;
  }
  if (message.kind === 'fault' && retired() && message.error === 'STALE_GENERATION') {
    send({ ...message, kind: 'retired_result_discarded', normal_retirement: true });
    return;
  }
  if (message.kind === 'fault' && channel) channel.stop(message.error === 'guard' ? 'budget' : 'fault');
  if (message.kind === 'private_done') {
    deferredPrivate.set(message.identity.request_id, { ...message, validated_cp: latestCP,
      sab_publications: publications, validation_events: completeCache?.events,
      NN_control_events: NNcontrolEvents, discarded_snapshots: discardedSnapshots,
      control_final: requestControl?.status(), player_binding: boundEngine });
    return; // Browser main asks for details after public/game progression.
  }
  send(message);
};

// Immutable 97 search, fixed PUCT1.5 Wasm and Sigma rules remain read-only.
importScripts('/original-worker.js');
const originalHandler = onmessage;
const originalCheck = check;
check = function(context, beforeNewWork = false) {
  synchronizeRetirement();
  return originalCheck(context, beforeNewWork);
};

function installSharedControlGuards() {
  const originalInfer = b.infer;
  const originalCall = b.call;
  b.infer = async function(bits) {
    if (synchronizeRetirement()) throw Error('STALE_GENERATION');
    const identity = requestIdentity;
    if (requestControl) Atomics.add(requestControl.words, 2, 1);
    const start = workerNow();
    try {
      const result = await originalInfer(bits);
      const discarded = synchronizeRetirement();
      NNcontrolEvents.push({ generation: identity?.generation ?? null, request_id: identity?.request_id ?? null,
        engine: boundEngine, start_ms: start, return_ms: workerNow(), result_discarded: !!discarded,
        session_run_start_ms: result.session_run_start_ms, session_run_end_ms: result.session_run_end_ms });
      // Return into the unchanged caller: its generation check rejects the old
      // result before resume/backup, while preserving actual NN completion logs.
      return result;
    } finally {
      if (requestControl) Atomics.add(requestControl.words, 3, 1);
    }
  };
  b.call = function(command) {
    if (['begin', 'resume'].includes(command.op) && synchronizeRetirement()) throw Error('STALE_GENERATION');
    return originalCall(command);
  };
}

onmessage = async function(event) {
  const data = event.data;
  if (data.identity && data.identity.engine !== boundEngine || data.engine && data.engine !== boundEngine) {
    send({ kind: 'failed', error: 'PLAYER_ENGINE_BINDING' }); return;
  }
  if (data.kind === 'get_private') {
    const row = deferredPrivate.get(data.request_id);
    if (!row) { send({ kind: 'failed', error: 'PRIVATE_MISSING' }); return; }
    deferredPrivate.delete(data.request_id); send(row); return;
  }
  if (data.kind === 'request') {
    if (active || activeNN || b.liveHandles()) { send({ kind: 'failed', error: 'OWN_PLAYER_NOT_REAPED' }); return; }
    const state = fromPrefix(data.identity.legal_prefix);
    requestIdentity = data.identity;
    requestControl = PlayerControl.bind(data.control, data.identity.generation);
    channel = SharedBestAction.bind(data.shared, data.shared_context, {
      generation: data.identity.generation, key: state._positionKey(), legalActions: state.getLegalActions().map(action => rustAction(state, action)) });
    requestClock = data.worker_clock;
    completeCache = new SnapshotCache(data.identity, { legal: state.getLegalActions().map(action => rustAction(state, action)),
      terminal: terminalResult(state), clock_error_ms: requestClock.error_ms + .2 }, () => workerNow() - requestClock.mid_ms);
    latestCP = null; publications = []; NNcontrolEvents = []; discardedSnapshots = 0;
  }
  await originalHandler(event);
  if (data.kind === 'load') installSharedControlGuards();
  if (data.kind === 'request') { requestControl = null; requestIdentity = null; }
};
