'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const ROOT=path.resolve(__dirname,'../..'),adapter=require('./adapters.cjs');
const document=JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/134-local-move-quality/preregister.json'));
for(const name of ['main','worker','producer','cache','checkpoint'])new vm.Script(adapter.script(name));
const context=vm.createContext({console,structuredClone,document,performance,SharedArrayBuffer,Atomics,TextEncoder,setTimeout,clearTimeout,setInterval,clearInterval});
for(const file of ['tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-cp-frame/shared-best-action.cjs','tools/ai-sigma-cp-frame/numeric-browser.js','tools/ai-sigma-player-workers/player-control.cjs'])vm.runInContext(fs.readFileSync(ROOT+'/'+file,'utf8'),context);
vm.runInContext(adapter.script('main'),context);
const preflight=vm.runInContext('qualityPreflight(document)',context);
const defects=vm.runInContext(`(()=>{
 const checks=[];
 for(const defect of ['Action','history','walls']){
  const selected=structuredClone(document.selected[0]);
  if(defect==='Action')selected.A.Action209=999;
  if(defect==='history')selected.fixture.history_counts.pop();
  if(defect==='walls')selected.fixture.board.walls_remaining[0]--;
  try{qualityForce(selected,'A');throw Error('FALSE_ACCEPT');}catch(error){if(error.message==='FALSE_ACCEPT')throw error;checks.push({defect,rejected:error.message});}
 }
 const memories=[1,2].map(generation=>({generation,key:'separate-'+generation,legalActions:[13]})).map(c=>({c,memory:SharedBestAction.create(c),control:PlayerControl.create(c.generation)}));
 const writers=memories.map(x=>SharedBestAction.bind(x.memory,x.c,x.c));
 assertIndependent=writers[0].words?.buffer!==writers[1].words?.buffer;
 if(memories[0].memory===memories[1].memory||memories[0].control===memories[1].control)throw Error('SHARED_CHANNEL');
 writers[0].publish({completed:true,sequence:1,action:13,value:.1,visits:1});
 if(writers[1].readLatest()!==null)throw Error('CROSS_PLAYER_PUBLICATION');
 return {checks,SAB_Control_separate:true,cross_player_publication:false};
})()`,context);
// Real adapted dispatch handler, with fake search function; no NN/browser/model.
const messages=[];
const producer=vm.createContext({performance,setTimeout,postMessage:m=>messages.push(m),importScripts:()=>{},structuredClone});
vm.runInContext(adapter.script('producer'),producer);
vm.runInContext("runReference=async(d)=>{postMessage({policy:'fixedSigma',slot:d.identity.engine});};run=async()=>{throw Error('CANDIDATE_SEARCH_CALLED');};",producer);
(async()=>{
 for(const engine of ['candidate','reference'])await vm.runInContext(`onmessage({data:{kind:'request',identity:{engine:'${engine}'}}})`,producer);
 assert.deepEqual(messages.map(x=>x.slot),['candidate','reference']);
 assert(messages.every(x=>x.policy==='fixedSigma'));
 const routing=await vm.runInContext(`(async()=>{
 const mockWorker1={},mockWorker2={};playerSlots.set('candidate',{worker:mockWorker1,cleanup:Promise.resolve()});playerSlots.set('reference',{worker:mockWorker2,cleanup:Promise.resolve()});return playerRoutingMock();
 })()`,context);
 console.log(JSON.stringify({preflight,defects,dispatch:messages,routing,browser:false,NN:0,real_model_sessions:0,clock_CPU_guarantee:false}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
