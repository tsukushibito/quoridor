async function loadSearchHost(){let inst;const compile=performance.now();const bytes=await(await fetch('/search.wasm')).arrayBuffer();inst=(await WebAssembly.instantiate(bytes,{env:{nn_now_ms:()=>performance.timeOrigin+performance.now(),probe_entropy:(p,n)=>{if(!crypto?.getRandomValues)return 1;const view=new Uint8Array(inst.exports.memory.buffer,p,n);for(let i=0;i<n;i+=65536)crypto.getRandomValues(view.subarray(i,Math.min(i+65536,n)));return 0;}}})).instance;const e=inst.exports;const compile_ms=performance.now()-compile;const alive=new Set();
function check(h){if(!alive.has(h))throw Error('stale host handle');return h}
function adopt(h){if(!h)throw Error('allocation rejected');alive.add(h);return h}
function put(v){let h=adopt(e.nn_buffer(v.length));new Uint8Array(e.memory.buffer,e.nn_ptr(h),v.length).set(v);return h}
function free(h){check(h);if(e.nn_free(h)!==1)throw Error('free rejected');alive.delete(h)}
function read(h){adopt(h);try{const b=new Uint8Array(e.memory.buffer,e.nn_ptr(h),e.nn_len(h));return JSON.parse(new TextDecoder().decode(b.slice()));}finally{free(h)}}
function checked(h){const r=read(h);if(!r.ok){let x=Error(r.error.detail);x.code=r.error.code;throw x}return r.data}
const owned=new Uint8Array(await(await fetch('/model.onnx')).arrayBuffer());const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',owned)),x=>x.toString(16).padStart(2,'0')).join('');if(digest!=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d')throw Error('MODEL_HASH');const b=put(owned);const start=performance.now();let model;try{model=adopt(checked(e.nn_load(b)).handle)}finally{free(b)}const load_ms=performance.now()-start;
function jsonCall(fn,value){const b=put(new TextEncoder().encode(JSON.stringify(value)));try{return checked(fn(b))}finally{free(b)}}
function create(req,diagnostic=false){return adopt(jsonCall(h=>e.nn_new(check(model),h,diagnostic?1:0),req).handle)}
function step(s,g){return checked(e.nn_step(check(s),g))}
function checkpoint(s,g){return checked(e.nn_checkpoint(check(s),g))}
function snapshot(s){return checked(e.nn_snapshot(check(s)))}
function diagnose(f){return jsonCall(h=>e.nn_diagnose(check(model),h),{fixtures:[f],raw_only:true}).fixtures[0]}
function faults(){let result={};for(const [name,v]of [["short_model",new Uint8Array([1,2,3])],["hash_model",(()=>{let v=owned.slice();v[0]^=1;return v})()]]){let b=put(v);try{result[name]=read(e.nn_load(b))}finally{free(b)}}let stale=put(new Uint8Array([1]));free(stale);try{check(stale)}catch(e){result.stale=e.message}return result}
function drop(){for(const h of [...alive])free(h);model=0}
return {e,alive,create,step,checkpoint,snapshot,diagnose,faults,free,drop,put,read,compile_ms,load_ms,digest};}
