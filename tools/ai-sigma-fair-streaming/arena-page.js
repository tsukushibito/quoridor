const epoch=()=>performance.timeOrigin+performance.now();let ref,candidate,refGen=0,candidateGen=0,handlers=new Map();
function wait(key,engine){return new Promise(resolve=>handlers.set(key,{resolve,engine:engine??(key.startsWith('ref-')?'reference':key.startsWith('candidate-')||key==='candidate-ready'||key==='numeric'?'candidate':key==='ref-ready'?'reference':null)}))}
function fire(key,data){const r=handlers.get(key);if(r){handlers.delete(key);r.resolve(data)}}
async function loadArena(){
 ref=new Worker('/ref/reference-worker.js?model=/models_9x9/best.onnx');ref.onmessage=({data})=>{if(data.type==='model_loaded'||data.type==='model_failed')fire('ref-ready',data);if(data.type==='response')fire(data.transaction?.request_id??('ref-'+data.generation),data)};
 let r=wait('ref-ready');const reference=await r;if(reference.type!=='model_loaded'||reference.threads!==1||reference.proxy!==false||reference.canonical!==true||JSON.stringify(reference.inputs)!=='["input"]'||JSON.stringify(reference.outputs)!=='["policy_logits","value"]')throw Error('REFERENCE_READY');
 candidate=new Worker('/candidate-worker.js');candidate.onmessage=({data})=>{if(data.kind==='model_faults')fire('model-faults',data);if(data.kind==='numeric')fire('numeric',data);if(data.kind==='ready'||data.kind==='failed')fire('candidate-ready',data);if(data.kind==='result'||data.kind==='clock_ping')fire(data.transaction?.request_id??('candidate-'+data.generation),data);};candidate.onerror=e=>{throw Error(e.message)};
 const c=wait('candidate-ready');candidate.postMessage({kind:'load'});const candidateReady=await c;if(candidateReady.kind!=='ready'||candidateReady.digest!=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'||candidateReady.threads!==1||candidateReady.proxy!==false)throw Error('CANDIDATE_LOAD_'+candidateReady.error);return {reference,candidate:candidateReady};
}
async function workerPing(engine,generation){if(engine==='reference'){const p=wait('ref-'+generation);ref.postMessage({type:'clock_ping',generation});return p;}const p=wait('candidate-'+generation);candidate.postMessage({kind:'clock_ping',generation});return p;}
async function dispatch(engine,request){const page_receive=epoch();const remaining=request.node_deadline_ms-(page_receive-request.page_offset_ms)-request.page_error_ms;
 if(remaining<=0)return {host_adapter_error:'PAGE_DEADLINE',page_receive,remaining};let p;
 if(engine==='reference'){p=wait(request.request_id,engine);ref.postMessage(request);}else{p=wait(request.request_id,engine);candidate.postMessage({kind:'request',request});}
 const payload=await p;if(request.diagnostic_corrupt_echo==='engine'&&payload.transaction)payload.transaction.engine='foreign';return {payload,page_receive,page_result:epoch(),remaining_on_page_arrival_ms:remaining};
}
async function injection(value,generation){const p=wait('ref-'+generation);ref.postMessage({type:'value_injection',value:value==='NaN'?NaN:value==='Infinity'?Infinity:value,generation});return p;}
function stopArena(){ref?.terminate();candidate?.terminate();}

function cancelEngine(engine,generation){if(engine==='reference')ref.postMessage({type:'cancel',generation});else candidate.postMessage({kind:'cancel',generation});return {sent:epoch(),generation};}

function abortEngine(engine){if(engine==='reference')ref?.terminate();else candidate?.terminate();for(const [key,h]of handlers){if(h.engine===engine){handlers.delete(key);h.resolve({transport_error:'BACKEND_STOPPED'});}}return {terminated:engine,at:epoch()};}

async function numericThree(fixtures){const p=wait('numeric');candidate.postMessage({kind:'numeric',fixtures});const wasm=await p,reference=[];for(let i=0;i<fixtures.length;i++){const generation=990000+i,q=wait('ref-'+generation);ref.postMessage({type:'numeric',generation,fixture:fixtures[i]});reference.push(await q);}return {wasm:wasm.result,reference};}
