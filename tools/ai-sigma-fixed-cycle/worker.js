const fixedInheritedHandler=onmessage;let fixedHandNN=0;
onmessage=async function(e){await fixedInheritedHandler(e);if(e.data.kind==='load'){const old=b.infer;b.infer=async function(bits){if(requestIdentity){if(fixedHandNN>=128)throw Error('FIXED_CYCLE_NN_BUDGET_REFUSAL');fixedHandNN++;}return old(bits);};}};
