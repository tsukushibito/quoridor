'use strict';
const q=require('../ai-sigma-nnue-qf1-prototype/qf1.cjs');
const {now,controlDrain}=require('../ai-sigma-native-baseline/common.cjs');
const A=Math.fround(.06294242415104226),B=Math.fround(8.276425107422213);
function input(s){const maps=q.maps(s),p=s.getCurrentPlayer(),d=[maps[0][s.player1pos[1]*9+s.player1pos[0]],maps[1][s.player2pos[1]*9+s.player2pos[0]]];if(!d.every(x=>Number.isInteger(x)&&x>=0&&x<=80))throw Error('DISTANCE_SCHEMA');return p===1?d:d.reverse();}
function value(s){const terminal=q.r.terminalResult(s);if(terminal)return terminal.value;const d=input(s),signal=Math.fround(Math.fround(d[1]/80)-Math.fround(d[0]/80));return Math.max(-1,Math.min(1,Math.fround(A+Math.fround(B*signal))));}
const history=s=>JSON.stringify([s._positionKey(),s.getCurrentPlayer(),[...s.position_history].sort(([a],[b])=>a<b?-1:a>b?1:0)]);
async function search(s,{generation,deadline_ms=Infinity,maxdepth=4,node_cap=8192,stop=()=>false,onCP=()=>{}}={}){
 const t=now(),key=s._positionKey(),hist=history(s),legal=s.getLegalActions(),stats={visited:0,processed:0,rejected_entry:0,evals:0,terminal:0,legal_calls:1,completed_depth:0,requested_depth:maxdepth,node_cap},before=q.stats();
 if(q.r.terminalResult(s))return{type:'ROOT_TERMINAL',cp:null,stats,zero:true};
 if(!legal.length)throw Error('ROOT_NOLEGAL');
 let completed={schema:'distance-alpha-v1',generation,action:q.r.rustAction(s,legal[0]),completed_depth:0,value:value(s),depth0_fallback:true};stats.evals++;
 const emit=()=>onCP({...completed,nodes:{...stats},maps:q.stats(),key,history:hist});emit();let typedStop=null,partialDepth=null;
 async function enter(){stats.visited++;if(stats.processed>=node_cap){stats.rejected_entry++;throw Error('NODE_CAP');}if(stop())throw Error('CANCELLED');if(now()>=deadline_ms)throw Error('TIME_CAP');stats.processed++;if(stats.processed%32===0){await controlDrain();if(stop())throw Error('CANCELLED');if(now()>=deadline_ms)throw Error('TIME_CAP');}}
 async function negamax(state,depth,alpha,beta){await enter();const terminal=q.r.terminalResult(state);if(terminal){stats.terminal++;return terminal.value;}if(depth===0){stats.evals++;return value(state);}stats.legal_calls++;let v=-Infinity;for(const action of state.getLegalActions()){const cv=-await negamax(state.next(action),depth-1,-beta,-alpha);v=Math.max(v,cv);alpha=Math.max(alpha,cv);if(alpha>=beta)break;}if(v===-Infinity)throw Error('INNER_NOLEGAL');return v;}
 for(let depth=1;depth<=maxdepth;depth++){
  await controlDrain();let best=null,v=-Infinity;
  try{await enter();for(const action of legal){const cv=-await negamax(s.next(action),depth-1,-Infinity,-v);if(cv>v){v=cv;best=action;}}stats.completed_depth=depth;completed={schema:'distance-alpha-v1',generation,action:q.r.rustAction(s,best),completed_depth:depth,value:v,depth0_fallback:false};emit();}
  catch(e){if(!['NODE_CAP','TIME_CAP','CANCELLED'].includes(e.message))throw e;typedStop=e.message;partialDepth=depth;break;}
 }
 if(s._positionKey()!==key||history(s)!==hist)throw Error('PARENT_STATE_CHANGED');
 return{cp:{...completed,nodes:{...stats},key,history:hist},stats,typed_stop:typedStop,partial_depth_discarded:partialDepth,elapsed_ms:now()-t,map_delta:{hits:q.stats().hits-before.hits,misses:q.stats().misses-before.misses,current:q.stats().current},NN_calls:0,zero:{active:false,activeNN:0,handles:0}};
}
module.exports={q,input,value,history,search,A,B};
