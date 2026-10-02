importScripts('/shared-best-action.js', '/snapshot-cache.js');
const sendDiagnostic = postMessage.bind(globalThis);
let channel = null;
let completeCache = null;
let latestCP = null;
let publications = [];
const deferredPrivate = new Map();

globalThis.postMessage = function(message) {
  if (message.kind === 'snapshot') {
    const begin = performance.timeOrigin + performance.now();
    if (completeCache.receive(message)) {
      const cp = completeCache.cache.owned.cp;
      channel.publish({completed:true, sequence:message.sequence, action:cp.action, value:message.value, visits:cp.simulations});
      latestCP = cp;
      publications.push({sequence:message.sequence, action:cp.action, validation_end_ms:performance.timeOrigin+performance.now(), begin_ms:begin});
    }
    return; // No per-CP Playwright / Node binding.
  }
  if (message.kind === 'fault' && channel) {
    if (message.error === 'guard') channel.stop('budget');
    else channel.stop('fault');
  }
  if (message.kind === 'private_done') {
    message.validated_cp = latestCP;
    message.sab_publications = publications;
    message.validation_events = completeCache?.events;
    deferredPrivate.set(message.identity.request_id,message);
    return; // Detailed payload delivered only after browser public and zero ACK.
  }
  sendDiagnostic(message);
};

importScripts('/original-worker.js');
const originalHandler = onmessage;
onmessage = async function(event) {
  const data = event.data;
  if(data.kind==='get_private') {
    const row=deferredPrivate.get(data.request_id);
    if(!row)throw Error('PRIVATE_MISSING');
    deferredPrivate.delete(data.request_id);sendDiagnostic(row);return;
  }
  if (data.kind === 'request') {
    const state = fromPrefix(data.identity.legal_prefix);
    channel = SharedBestAction.bind(data.shared, data.shared_context, {generation:data.identity.generation,key:state._positionKey(),legalActions:state.getLegalActions().map(action=>rustAction(state,action))});
    completeCache = new SnapshotCache(data.identity, {
      legal:state.getLegalActions().map(action=>rustAction(state,action)),
      terminal:terminalResult(state), clock_error_ms:1,
    }, ()=>performance.timeOrigin+performance.now());
    latestCP = null;
    publications = [];
  }
  return originalHandler(event);
};
