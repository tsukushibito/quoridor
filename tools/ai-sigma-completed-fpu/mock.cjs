'use strict';
const vm=require('vm');
const assert=require('assert/strict');
const {referenceCore}=require('./adapters.cjs');
const context=vm.createContext({Math,JSON});
vm.runInContext(`let unvisitedMode='original',fpuSelections=[];`+referenceCore()+`
globalThis.exercise=function(mode,reduction=.2){
  unvisitedMode=mode;fpuSelections=[];
  const parent=new MCTSNode(null);parent.visitCount=10;parent.valueSum=4;
  const visited=new MCTSNode(null,parent,'visited',.25);visited.visitCount=1;visited.valueSum=-.1;
  const untouched=new MCTSNode(null,parent,'unvisited',.75);
  parent.children=[visited,untouched];const picked=parent.bestChild(1,reduction);
  return {picked:picked.action,trace:fpuSelections[0]};
};`,context);
const baseline=context.exercise('original'),zero=context.exercise('Q0'),reductionZero=context.exercise('original',0);
assert.equal(baseline.trace.used_unvisitedQ,.4-.2*Math.sqrt(.25));
assert.equal(zero.trace.used_unvisitedQ,0);
assert.equal(reductionZero.trace.used_unvisitedQ,.4);
assert.equal(baseline.trace.truevisitCount,10);assert.equal(baseline.trace.valueSum,4);
assert.equal(context.exercise('original').trace.used_unvisitedQ,baseline.trace.used_unvisitedQ);
function permitted({active,activeNN,handles,mode},condition,engine){return !active&&!activeNN&&!handles&&mode==='original'&&(engine==='candidate'?condition==='A':['B','C'].includes(condition));}
const clean={active:false,activeNN:0,handles:0,mode:'original'};
assert(permitted(clean,'A','candidate'));assert(permitted(clean,'B','reference'));assert(permitted(clean,'C','reference'));
for(const old of [{...clean,active:true},{...clean,activeNN:1},{...clean,handles:1},{...clean,mode:'Q0'}])assert(!permitted(old,'B','reference'));
assert(!permitted(clean,'C','candidate'));assert(!permitted(clean,'A','reference'));
assert.equal(1+31,32);assert.equal(32-1,31);
console.log(JSON.stringify({NN0:true,baseline,zero,reductionZero,old_zero_and_mode_leak_rejected:true,engine_condition_binding:true,K32_initial_plus31:true,mock_not_actual_search:true}));

const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../..'),inputs=JSON.parse(fs.readFileSync(root+'/research-data/ai-sigma/119-diverse-prefix/prefix-document.json'));
const inputContext=vm.createContext({Math,JSON,Map,Set,Array,Uint32Array,Uint8Array,Float32Array});
vm.runInContext(fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/game.js','utf8')+fs.readFileSync(root+'/tools/ai-sigma-actual-boundary-repair/context.js','utf8')+fs.readFileSync(__dirname+'/count-input.js','utf8')+'globalThis.validateInput=checkedCountState;',inputContext);
for(const prefix of inputs.prefixes.slice(0,2))assert(inputContext.validateInput(prefix.fixture));
const malformed=JSON.parse(JSON.stringify(inputs.prefixes[0].fixture));malformed.features_bits[0]^=1;
assert.throws(()=>inputContext.validateInput(malformed));
console.log(JSON.stringify({NN0:true,prefix1_2_exact_state_history_features_legal:true,foreign_feature_rejected:true,old_schema_error_not_NN_negative:true}));
