'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const base=require('../ai-sigma-cpu-sigma-frame8/adapters.cjs');
function replaceExactly(source,before,after){if(source.split(before).length!==2)throw Error('ADAPTER_SOURCE_COUNT');return source.replace(before,after);}
function script(name){
  let text=base.script(name);
  if(name==='main'){
    text=replaceExactly(text,'let state=referenceState(fixture);','let state=diversePrefixState(fixture);');
    // Keep light parsing/identity checks and old post-game numeric validation; add no per-turn Node work.
    text=replaceExactly(text,'row.own_previous_wait={start_ms:ownWaitStart,end_ms:ownWaitEnd,wait_ms:ownWaitEnd-ownWaitStart};','row.own_previous_wait={input_available_ms:ownWaitStart,start_ms:ownWaitStart,end_ms:ownWaitEnd,wait_ms:ownWaitEnd-ownWaitStart,ready_t0_ms:t0};');
    text+='\n'+fs.readFileSync(__dirname+'/prefix-browser.js','utf8');
  }
  return text;
}
function bindings(){const old=base.bindings();return Object.fromEntries(Object.entries(old).map(([name,v])=>[name,{...v,adapted_SHA256:crypto.createHash('sha256').update(script(name)).digest('hex'),adapter117_readonly:true}]));}
module.exports={script,bindings};
