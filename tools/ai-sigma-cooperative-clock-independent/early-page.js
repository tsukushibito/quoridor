async function forward(name,m){m.transport.page_binding_begin_ms=performance.timeOrigin+performance.now();try{return await globalThis[name](m);}finally{m.transport.page_binding_end_ms=performance.timeOrigin+performance.now();bindingMarkers.push({kind:m.kind,request_id:m.identity?.request_id,...m.transport});}}
const bindingMarkers=[];let worker;const privateRows={},waiters=new Map();let pingSeq=0;
function waiting(key){return new Promise(r=>waiters.set(key,r));}function resolve(key,v){const r=waiters.get(key);if(r){waiters.delete(key);r(v);}}
function setupEarly(){worker=new Worker('/early-worker.js');worker.onmessage=({data:m})=>{const at=performance.timeOrigin+performance.now();m.transport={page_received_ms:at,page_binding_begin_ms:null,page_binding_end_ms:null};if(m.kind==='snapshot'||m.kind==='fault')void forward('publishCompleted',m);else if(m.kind==='stopped')void forward('publishStopped',m);else if(m.kind==='private_done')privateRows[m.identity.request_id]=m;else if(m.kind==='startup_root')resolve('startup-root',m);else if(m.kind==='ready'||m.kind==='failed'){resolve('ready',m);if(m.kind==='failed')resolve('startup-root',m);}else if(m.kind==='ping')resolve('ping-'+m.id,m);else if(m.kind==='dropped')resolve('dropped',m);};worker.onerror=e=>{const error_detail={name:'WorkerErrorEvent',message:e.message,filename:e.filename,lineno:e.lineno,colno:e.colno};void publishCompleted({kind:'unbound_worker_error',error:e.message,error_detail,producer_time_unknown:true});resolve('ready',{kind:'failed',error:e.message,error_detail});};return true;}
function loadEarly(){const p=waiting('ready');worker.postMessage({kind:'load'});return p;}function pingEarly(){const id=++pingSeq,p=waiting('ping-'+id);worker.postMessage({kind:'ping',id});return p;}
function sendEarly(d){worker.postMessage(d);return {page_send_ms:performance.timeOrigin+performance.now()};}
function cancelEarly(generation){worker.postMessage({kind:'cancel',generation});return {at_ms:performance.timeOrigin+performance.now()};}
function privateEarly(){return privateRows;}
async function dropEarly(){const p=waiting('dropped');worker.postMessage({kind:'drop'});return await p;}
function terminateEarly(){worker.terminate();return {forced:true,at_ms:performance.timeOrigin+performance.now()};}

function startupRootEarly(engine,fixture){const p=waiting('startup-root');worker.postMessage({kind:'startup_root',engine,fixture});return p;}

function tailBindingMarkers(id){return bindingMarkers.filter(x=>x.request_id===id);}
