'use strict';
// Owner NN0 replay of saved public Actions and first roots, after scientific stop.
const fs=require('fs'),assert=require('assert'),{createReference}=require('../ai-sigma-native-baseline/reference.cjs'),{A,D,save}=require('./common.cjs'),{r}=createReference();
const rows=p=>fs.existsSync(p)?fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
const result=[],rootpairs=[],rootExports=[];for(const run of ['native173-quality-r1','native173-quality-e2-r1']){
 const p=JSON.parse(fs.readFileSync(A+'/runs/'+run+'.process.json'));assert(!p.remaining.length&&!p.unknown_adopted.length,'NOT_STOPPED');
 for(const core of [2,4,6]){const base=A+'/runs/'+run+'/core'+core,journal=rows(base+'/journal.jsonl'),games=rows(base+'/games.jsonl');
  for(const pair of new Set(games.map(g=>g.pair))){const rr=games.filter(g=>g.pair===pair).map(g=>g.firstRoot);const available=rr.length===2&&rr.every(r=>r&&r.NN137_bits?.length===137);if(available){assert(JSON.stringify(rr[0].NN137_bits)===JSON.stringify(rr[1].NN137_bits),'PAIR_NN137_BITS');assert(JSON.stringify(rr[0].features648_bits)===JSON.stringify(rr[1].features648_bits),'PAIR_ROOT648_BITS');}rootpairs.push({run,pair,NN137_two_color_bits_equal:available?true:null,features648_two_color_bits_equal:available?true:null});}
  for(const g of games){const initial=g.firstRoot;if(!initial){result.push({run,game_id:g.game_id,status:'NO_ROOT_UNKNOWN'});continue;}
   let state=r.fromPrefix(initial.legal_prefix),prefix=structuredClone(initial.legal_prefix);const js=journal.filter(x=>x.game_id===g.game_id);let applied=0,knownClock=0;
   const visits=Array(136).fill(0),legalRoot=state.getLegalActions(),perm=r.vertPolicyPermutation(9);for(const [action,prior,N,valueSum] of initial.rootvisits??[]){const a=legalRoot.find(a=>r.rustAction(state,a)===action);assert(a,'PI_ACTION_LEGAL');assert(Number.isInteger(N)&&N>=0,'PI_VISIT_COUNT');const real=r.actionToIndex(a,9),canonical=initial.side===2?perm[real]:real;visits[canonical]+=N;}
   const total=visits.reduce((a,b)=>a+b,0),z=g.winner===0?0:g.winner===1?1:g.winner===2?-1:null;
   rootExports.push({run,game_id:g.game_id,pair:g.pair,lineage_group:run+'-pair-'+g.pair,holdout:true,training_use:false,player:initial.side,view:'side-to-move; P2 vertical policy permutation',features648_bits:initial.features648_bits,NN137_bits:initial.NN137_bits,leafNN:initial.rootNN_leaf,rootmean:initial.rootmean,pi136:total?visits.map(n=>n/total):null,root_visit_counts136:visits,root_visit_total:total,terminal_z_P1:z,terminal_z_side:z===null?null:initial.side===1?z:-z,teacher_budget:initial.teacher_budget,quality_qualification:'join all-slots by game_id; raw terminal does not establish clock qualification'});
   assert(JSON.stringify(r.portState(state))===JSON.stringify(initial.root_state),'ROOT_STATE');assert(JSON.stringify(r.portState(state).features_bits)===JSON.stringify(initial.features648_bits),'ROOT_FEATURES');
   for(const j of js){assert(j.key===state._positionKey()&&j.ply===state.depth,'STATE_KEY_HISTORY');if(j.status!=='COMPLETE')break;
    assert(j.public_cp&&j.public_cp.admit_ms<=402&&j.public_actual_ms<=500,'CLOCK');assert(j.NN_calls===j.NN_returned&&j.zero.activeNN===0&&j.zero.handles===0&&!j.zero.active,'NN_ZERO');knownClock++;
    const legal=state.getLegalActions(),move=legal.find(a=>r.rustAction(state,a)===j.public_cp.action);assert(move,'ILLEGAL_PUBLIC');prefix.push(move);state=state.next(move);applied++;
   }
   assert(JSON.stringify(prefix)===JSON.stringify(g.legal_prefix),'SAVED_FULL_PREFIX');assert(state._positionKey()===g.final_key&&state.depth===g.final_ply,'FINAL_STATE');
   const terminal=r.terminalResult(state);if(['GOAL','DRAW200','DRAW_NOLEGAL'].includes(g.status))assert(terminal&&terminal.winner===g.winner,'TERMINAL');
   result.push({run,game_id:g.game_id,status:g.status,applied_legal_actions:applied,clock_complete_rows:knownClock,root648_equal:true,root137_count:initial.NN137_bits?.length??null,final_key_equal:true,terminal_equal:!!terminal,quality_qualification_independent_of_this_owner_replay:true});
  }
 }
}
save(D+'/holdout-root-export.json',{schema:'formal holdout first-root leafNN/rootmean/pi136/z separate; no learning',rows:rootExports});save(D+'/owner-replay.json',{NN:0,rows:result,rootpairs,shared_rules_independence_limit:'same frozen RuleA/reference decoder; not independent checker',root137_between_policies_bitwise_all_roots_comparison:'saved roots only; no new NN',new_science:0});console.log(JSON.stringify({games:result.length,actions:result.reduce((s,x)=>s+(x.applied_legal_actions??0),0),NN:0}));
