'use strict';
// NN0 prototype for a NEW formal adapter; no existing adapter is modified.
const RULE = Object.freeze({cutoff:402, adopt:411, public:500, cycle:1000, startLate:5});
const finite = x => typeof x === 'number' && Number.isFinite(x);
const interval = x => x && finite(x.lo) && finite(x.hi) && x.lo <= x.hi;
function cpAdmission(cp, identity, legal, lastSequence, mainReadAdmit) {
  if (!interval(mainReadAdmit)) return {accepted:false, type:'CLOCK_INTERVAL_UNKNOWN'};
  if (mainReadAdmit.lo < identity.t0) return {accepted:false, type:'CLOCK_ORDER_UNKNOWN'};
  if (mainReadAdmit.hi >= identity.t0 + RULE.cutoff) {
    return {accepted:false, type:mainReadAdmit.lo >= identity.t0+RULE.cutoff ? 'CP_AFTER_CUTOFF':'CP_BOUNDARY_UNKNOWN'};
  }
  if (!cp || cp.stable !== true) return {accepted:false, type:'CP_COHERENCE_UNKNOWN'};
  if (cp.generation !== identity.generation || cp.key !== identity.key) return {accepted:false, type:'STALE_CP'};
  if (!Number.isSafeInteger(cp.sequence) || cp.sequence <= lastSequence) return {accepted:false, type:'CP_SEQUENCE_INVALID'};
  if (!Number.isSafeInteger(cp.action) || !legal.includes(cp.action)) return {accepted:false, type:'ILLEGAL_PUBLIC_ACTION'};
  return {accepted:true, type:'MAIN_CAUSAL_PRE_CUTOFF', cp:{...cp}, mainReadAdmit:{...mainReadAdmit}, exactAtomicstore:null};
}
function workerOnlyEvidence(mappedInterval, cutoff) {
  if (!interval(mappedInterval)) return 'WORKER_CLOCK_UNKNOWN';
  if (mappedInterval.hi < cutoff) return 'UPPER_PRE_CUTOFF';
  if (mappedInterval.lo >= cutoff) return 'LOWER_AFTER_CUTOFF';
  return 'BOUNDARY_UNKNOWN';
}
function publicDecision(cached, identity, stamp) {
  if (!interval(stamp)) return {valid:false,type:'PUBLIC_CLOCK_UNKNOWN',quality:[0,1]};
  if (stamp.lo < identity.t0+RULE.adopt) return {valid:false,type:'PUBLIC_BEFORE_PLANNED_ADOPT',quality:[0,1]};
  if (stamp.hi >= identity.t0+RULE.public) return {valid:false,type:'PUBLIC_DEADLINE_UNKNOWN_OR_LATE',quality:[0,1]};
  if (!cached?.accepted) return {valid:false,type:'NO_CERTIFIED_CP',quality:[0,1]};
  return {valid:true,type:'PUBLIC_WITHIN_500',action:cached.cp.action,sequence:cached.cp.sequence,stamp};
}
function nextCycle(identity, oldACK, readyAt) {
  const nextTarget=identity.t0+RULE.cycle;
  if (!interval(readyAt)) return {start:false,type:'NEXT_CLOCK_UNKNOWN',nextTarget};
  if (!oldACK || oldACK.request!==identity.request || oldACK.generation!==identity.generation)
    return {start:false,type:'OLD_ACK_UNKNOWN',nextTarget};
  const fields=['active','activeNN','handles','live_searches','pending_eval','pending_publish'];
  if (fields.some(k=>oldACK[k]!==0) || !Number.isSafeInteger(oldACK.started) || oldACK.started<0 || oldACK.started!==oldACK.returned)
    return {start:false,type:'OLD_REQUEST_NOT_QUIESCENT',nextTarget};
  if (!finite(oldACK.mainReceived) || oldACK.mainReceived < identity.t0 || oldACK.mainReceived > nextTarget)
    return {start:false,type:'TAIL_CYCLE_OVERRUN_OR_UNKNOWN',nextTarget};
  if (readyAt.lo < nextTarget || readyAt.hi > nextTarget+RULE.startLate)
    return {start:false,type:'NEXT_CYCLE_CLOCK_MISS',nextTarget};
  return {start:true,type:'APPLICATION_QUIESCENT_CYCLE',nextTarget, tailACKwall:oldACK.mainReceived-identity.t0,
    kernelCPU:null, backendThreadBinding:null, formalReady:false};
}
// All words are atomic. The clock must bracket read AND legal/identity checks
// in the real main receiver; mock clocks below do not validate browser clocks.
function readStable(words, clock, key) {
  const lo=clock(), rev1=Atomics.load(words,0);
  const cp={generation:Atomics.load(words,1),sequence:Atomics.load(words,2),action:Atomics.load(words,3),key};
  const rev2=Atomics.load(words,0),hi=clock();
  return {cp:{...cp,stable:rev1===rev2 && !(rev1&1)},readBracket:{lo,hi}};
}
module.exports={RULE,cpAdmission,workerOnlyEvidence,publicDecision,nextCycle,readStable};
