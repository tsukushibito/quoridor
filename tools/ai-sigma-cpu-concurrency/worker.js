'use strict';
// Resource refusal only, not a search parameter. Startup calls are separate.
const concInheritedHandler=onmessage;let concHandNN=0;
onmessage=async function(e){await concInheritedHandler(e);if(e.data.kind==='load'){const old=b.infer;b.infer=async function(bits){if(requestIdentity){if(concHandNN>=102)throw Error('CONCURRENCY_NN_BUDGET_REFUSAL');concHandNN++;}return old(bits);};}};
