'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const SharedBestAction=require('../ai-sigma-cp-frame/shared-best-action.cjs');
const PlayerControl=require('./player-control.cjs');
const workers=[];
class FakeWorker {
  constructor(url){this.url=url;workers.push(this);}
  postMessage(message){this.last=message;}
  terminate(){this.terminated=true;}
}
async function main(){
  const context=vm.createContext({SharedBestAction,PlayerControl,Worker:FakeWorker,performance,
    setTimeout,clearTimeout,setInterval,clearInterval,console});
  vm.runInContext(fs.readFileSync(__dirname+'/player-main.js','utf8'),context);
  assert.equal(vm.runInContext('setupEarly().separate_Workers',context),true);
  const row=await vm.runInContext('playerRoutingMock()',context);
  const a=vm.runInContext("waitingMessage('candidate-ping')",context);
  const b=vm.runInContext("waitingMessage('reference-ping')",context);
  workers[1].onmessage({data:{kind:'ping',worker_engine:'reference',at_ms:22}});
  workers[0].onmessage({data:{kind:'ping',worker_engine:'candidate',at_ms:11}});
  assert.equal((await a).at_ms,11);assert.equal((await b).at_ms,22);
  assert.equal(vm.runInContext('waitingMessages.size',context),0);
  vm.runInContext('terminateEarly()',context);
  console.log(JSON.stringify({...row,reverse_order_message_routing:true,terminated:workers.every(w=>w.terminated)}));
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
