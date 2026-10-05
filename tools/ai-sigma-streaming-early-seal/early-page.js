let worker;const privateRows={},waiters=new Map();let pingSeq=0;
function waiting(key){return new Promise(r=>waiters.set(key,r));}function resolve(key,v){const r=waiters.get(key);if(r){waiters.delete(key);r(v);}}
function setupEarly(){worker=new Worker('/early-worker.js');worker.onmessage=({data:m})=>{if(m.kind==='snapshot'||m.kind==='fault')void publishCompleted(m);else if(m.kind==='stopped')void publishStopped(m);else if(m.kind==='private_done')privateRows[m.identity.request_id]=m;else if(m.kind==='ready'||m.kind==='failed')resolve('ready',m);else if(m.kind==='ping')resolve('ping-'+m.id,m);else if(m.kind==='dropped')resolve('dropped',m);};worker.onerror=e=>void publishCompleted({kind:'unbound_worker_error',error:e.message,producer_time_unknown:true});return true;}
function loadEarly(){const p=waiting('ready');worker.postMessage({kind:'load'});return p;}function pingEarly(){const id=++pingSeq,p=waiting('ping-'+id);worker.postMessage({kind:'ping',id});return p;}
function sendEarly(d){worker.postMessage(d);return {page_send_ms:performance.timeOrigin+performance.now()};}
function cancelEarly(generation){worker.postMessage({kind:'cancel',generation});return {at_ms:performance.timeOrigin+performance.now()};}
function privateEarly(){return privateRows;}
async function dropEarly(){const p=waiting('dropped');worker.postMessage({kind:'drop'});return await p;}
function terminateEarly(){worker.terminate();return {forced:true,at_ms:performance.timeOrigin+performance.now()};}
