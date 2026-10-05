'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert');
const {r}=require('../ai-sigma-native-baseline/reference.cjs').createReference();
const D=path.resolve(__dirname,'../../research-data/ai-sigma/frame14-l2-test');
const file=D+'/openings.json';assert(!fs.existsSync(file),'ALREADY_FROZEN');
const master=crypto.randomBytes(32).toString('hex'),sha=x=>crypto.createHash('sha256').update(x).digest('hex');
function opening(slot,length){const attempts=[];for(let a=0;a<256;a++){
 const seed=sha('FRAME14_198_OPENING_V1|'+master+'|'+slot+'|'+a);let x=parseInt(seed.slice(0,8),16)||1;
 const u=()=>{x^=x<<13;x^=x>>>17;x^=x<<5;x>>>=0;return x/4294967296;};
 let state=r.fromPrefix([]),prefix=[],reason=null;
 for(let p=0;p<length;p++){
  if(r.terminalResult(state)){reason='INTERMEDIATE_TERMINAL';break;}
  const kind=u()<.5?'pawn':'wall',legal=state.getLegalActions().filter(z=>z.type===kind);
  if(!legal.length){reason='CHOSEN_EMPTY_CATEGORY';break;}
  const action=legal[Math.floor(u()*legal.length)];prefix.push(action);state=state.next(action);
 }
 if(!reason&&r.terminalResult(state))reason='FINAL_TERMINAL';attempts.push({proposal:a+1,seed,reason});
 if(!reason)return{generated:true,opening:{legal_prefix:prefix,key:state._positionKey(),side:state.getCurrentPlayer(),ply:state.depth,seed,proposal:a+1,root_state:r.portState(state)},attempts};
}return{generated:false,opening:null,attempts};}
const jobs=[['test','test']];
const games=[];
for(const [job,split]of jobs)for(let i=0;i<24;i++){
 const slot=games.length+1,family='frame14-198-'+sha('FAMILY|'+master+'|'+job+'|'+i),target_ply=[8,12,16,20,24,28][i%6];
 games.push({game_id:'native198-'+job+'-'+String(i+1).padStart(2,'0'),job,split,family,lineage:family,slot,partition_slot:split==='train'?(+job.slice(-2)-1)*24+i+1:i+1,core:[2,4,6][i%3],target_ply,sampling_seed:sha('FRAME14_198_ACTION_V1|'+family),...opening(slot,target_ply)});
}
assert.equal(new Set(games.map(g=>g.family)).size,24);assert.equal(new Set(games.map(g=>g.sampling_seed)).size,24);
const signatures=new Map;for(const g of games.filter(g=>g.generated)){const s=g.opening.key;if(!signatures.has(s))signatures.set(s,[]);signatures.get(s).push(g.game_id);}
for(const g of games)g.opening_duplicate_flag=g.generated&&signatures.get(g.opening.key).length>1;
const manifest={issue:'quoridor-4lc.198',UTC:new Date().toISOString(),master,domain:'FRAME14_198_OPENING_V1',generation:{target_once_fixed:true,category:'one pawn/wall draw .5 per ply; legal category order original; within uniform',empty:'chosen empty category rejects whole proposal',terminal:'any intermediate/final terminal rejects whole proposal',max_proposals:256,accept:'firstaccepted',seed_replacement:false,duplicate:'flag retained, no winner/value filtering'},jobs:jobs.map(x=>x[0]),split:{train:0,validation:0,test:24,siblings_same_family:true},games,NN:0,old173_read:0,oldteacher_reuse:0};
fs.writeFileSync(file,JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({generated:games.filter(g=>g.generated).length,unknown:games.filter(g=>!g.generated).length,SHA256:sha(fs.readFileSync(file)),NN:0}));
