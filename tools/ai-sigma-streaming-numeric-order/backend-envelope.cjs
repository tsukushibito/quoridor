'use strict';const C=require('./caller.cjs');
// Real worker emits this kind/error/identity envelope; mocks inject at this same receiver.
function receiveHost(c,m){if(!m||JSON.stringify(m.identity)!==JSON.stringify(c.identity)){c.cache.invalidate('FINAL_IDENTITY');return false;}const ok=C.receive(c,m);if(ok)c.producerEcho=m.producer_identity??m.identity;return ok;}
function hostFault(c,error){return receiveHost(c,{kind:'fault',identity:c.identity,error,producer_fault_ms:c.now?c.now():C.now(),sent_ms:(c.now?c.now():C.now())+(c.clock?.worker.lo_ms??0)});}
module.exports={receiveHost,hostFault};
