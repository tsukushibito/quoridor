'use strict';
const fs=require('fs');
const path=require('path');
const crypto=require('crypto');
const original=require('../ai-sigma-diverse-prefix/adapters.cjs');
const root=path.resolve(__dirname,'../..');
function replaceOnce(source,before,after){
  if(source.split(before).length!==2)throw Error('FPU_SOURCE_BINDING');
  return source.replace(before,after);
}
function referenceCore(){
  const source=fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/reference-core.js','utf8');
  let adapted=replaceOnce(source,'? pq - fpuReduction * Math.sqrt(visitedPriorSum)','? (unvisitedMode === "Q0" ? 0 : pq - fpuReduction * Math.sqrt(visitedPriorSum))');
  adapted=replaceOnce(adapted,'let best = null, bestScore = -Infinity;',`if(this.parent===null) fpuSelections.push({truevisitCount:this.visitCount,valueSum:this.valueSum,parentQ:pq,visitedChildBasePriorSum:visitedPriorSum,original_unvisitedQ:pq-fpuReduction*Math.sqrt(visitedPriorSum),used_unvisitedQ:unvisitedMode==='Q0'?0:pq-fpuReduction*Math.sqrt(visitedPriorSum),mode:unvisitedMode});
    let best = null, bestScore = -Infinity;`);
  return adapted;
}
function script(name){
  if(name==='reference')return referenceCore();
  if(name==='main')return original.script('main')+'\n'+fs.readFileSync(__dirname+'/count-input.js','utf8')+'\n'+fs.readFileSync(__dirname+'/count-main.js','utf8');
  if(name==='worker')return fs.readFileSync(__dirname+'/count-worker.js','utf8');
  return original.script(name);
}
function bindings(){
  return {...original.bindings(),FPU_reference:{original_path:'tools/ai-sigma-actual-boundary-repair/reference-core.js',original_SHA256:crypto.createHash('sha256').update(fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/reference-core.js')).digest('hex'),adapted_SHA256:crypto.createHash('sha256').update(referenceCore()).digest('hex'),factor:'unvisitedQ only; same root instrumentation B/C'}};
}
module.exports={script,bindings,referenceCore};
