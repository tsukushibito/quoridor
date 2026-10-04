"use strict";
// Standalone artifact. No model, policy, TT, shared source edits or arena import.
const {createReference}=require('../ai-sigma-native-baseline/reference.cjs');
const {r}=createReference();
const VERSION='RuleA-node-context-v1';
const known=new WeakMap();
const methods=['winner','getCurrentPlayer','getLegalActions','_positionKey','_getLegalPawnActions','_getLegalWallActions'];
function fail(code){const e=new Error(code);e.code=code;throw e;}
function stamp(s){
 if(!(s instanceof r.State)||s.boardsize!==9)fail('UNSUPPORTED_STATE');
 const set=x=>Array.from(x).sort(),hist=Array.from(s.position_history).sort(([a],[b])=>a<b?-1:a>b?1:0);
 return JSON.stringify([VERSION,s.boardsize,s.depth,s.getCurrentPlayer(),s._positionKey(),s.player1pos,s.player2pos,s.walls_p1,s.walls_p2,s.walls_initial,
 Array.from(s.hwalls),Array.from(s.vwalls),set(s.hwall_anchors),set(s.vwall_anchors),hist,Array.from(s.p1_dist),Array.from(s.p2_dist),set(s.p1_path_edges),set(s.p2_path_edges),s._legal_actions_cache]);
}
function createNodeContext(s,context){
 if(typeof context!=='string'||!context)fail('CONTEXT_REQUIRED');
 const before=stamp(s),prior=known.get(s);
 if(prior!==undefined&&prior!==before)fail('STATE_MUTATED_RECONSTRUCT_REQUIRED');
 const fns=methods.map(k=>s[k]);
 const terminal=r.terminalResult(s);
 const legal=terminal?null:s.getLegalActions();
 const actions=legal===null?null:Object.freeze(Array.from(legal,a=>a.type==='pawn'?Object.freeze({type:'pawn',direction:Object.freeze(Array.from(a.direction))}):Object.freeze({type:'wall',x:a.x,y:a.y,orientation:a.orientation})));
 const snapshot=stamp(s);known.set(s,snapshot);
 const result=Object.freeze({version:VERSION,context,terminal:terminal?Object.freeze({...terminal}):null,legal:actions});
 let live=true;
 function read(current,key,{cancelled=false}={}){
  if(!live)fail('NODE_CONTEXT_INVALIDATED');
  if(cancelled){live=false;fail('CANCELLED');}
  if(current!==s||key!==context){live=false;fail('IDENTITY_OR_CONTEXT_CHANGED');}
  if(methods.some((k,i)=>s[k]!==fns[i])||stamp(s)!==snapshot){live=false;fail('STATE_MUTATED');}
  return result;
 }
 return Object.freeze({read,dispose(){live=false;},version:VERSION});
}
module.exports={VERSION,r,createNodeContext,stamp};
