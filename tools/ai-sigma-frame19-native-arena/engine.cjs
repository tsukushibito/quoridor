'use strict';
const assert=require('assert'),n=require('../ai-sigma-frame18-native-connection/native.cjs'),{q}=n;
const now=()=>Number(process.hrtime.bigint())/1e6;
function search(root,engine,weights,manifest,options={}){
 const begin=now(),key=root._positionKey(),history=n.history(root),maps=q.stats();
 const stats={visited:0,processed:0,rejected_entry:0,NN:0,D_evals:0,terminal:0,legal_calls:0,full_accum:0,delta_accum:0,clone:0,cutoffs:0,control:0};
 const spans={control_ms:0,terminal_inclusive_ms:0,legal_order_inclusive_ms:0,clone_ms:0,input_full_delta_inclusive_ms:0,evaluator_inclusive_ms:0};
 const cap=options.nodeCap??8192,deadline=options.deadlineMs??Infinity,maxdepth=options.maxDepth??64,ordering=options.ordering??'rootbest-first';let completed=null,typedStop=null,discard=null;
 const measure=(name,fn)=>{const a=now();try{return fn()}finally{spans[name]+=now()-a}};
 function control(){measure('control_ms',()=>{stats.control++;if(now()>=deadline)throw Error('INTERNAL_DEADLINE');if(options.stop&&options.stop())throw Error('CANCELLED')})}
 function call(name,fn){control();const v=measure(name,fn);control();return v}
 function enter(){control();stats.visited++;if(stats.processed>=cap){stats.rejected_entry++;throw Error('NODE_CAP')}stats.processed++}
 function terminal(s){return call('terminal_inclusive_ms',()=>q.r.terminalResult(s))}
 function ordered(s){stats.legal_calls++;return call('legal_order_inclusive_ms',()=>s.getLegalActions().map(action=>({action,Action:q.r.rustAction(s,action)})).sort((a,b)=>a.Action-b.Action))}
 function child(s,action){stats.clone++;return call('clone_ms',()=>s.next(action))}
 function delta(a,s){if(engine!=='NNUE')return null;stats.delta_accum++;return call('input_full_delta_inclusive_ms',()=>q.delta(a,s,weights))}
 function evaluate(s,a){return call('evaluator_inclusive_ms',()=>{if(engine==='NNUE'){if(options.onNN)options.onNN();stats.NN++;return n.valueScaled(a,weights,manifest)}stats.D_evals++;return n.distance(s,manifest)})}
 function negamax(s,a,depth,alpha,beta){enter();const t=terminal(s);if(t){stats.terminal++;return t.value}if(!depth)return evaluate(s,a);let value=-Infinity;for(const item of ordered(s)){const c=child(s,item.action),v=-negamax(c,delta(a,c),depth-1,-beta,-alpha);if(v>value)value=v;if(v>alpha)alpha=v;if(alpha>=beta){stats.cutoffs++;break}}assert(Number.isFinite(value),'NOLEGAL_NONTERMINAL');return value}
 const depths=[];let legal=[],acc=null,terminalValue=null;
 try{
 const t=terminal(root);if(t){terminalValue=t;return {status:'TERMINAL',terminal:t,stats,spans,wholewall_ms:now()-begin,NN:0}}
 legal=ordered(root);assert(legal.length);
 if(engine==='NNUE'){stats.full_accum++;acc=call('input_full_delta_inclusive_ms',()=>q.full(root,weights))}
 for(let depth=1;depth<=maxdepth;depth++){
 const before={...stats},start=now();let value=-Infinity,best=null;const rootOrder=legal.slice();
 if(ordering==='rootbest-first'&&completed){const i=rootOrder.findIndex(x=>x.Action===completed.Action);assert(i>=0);rootOrder.unshift(...rootOrder.splice(i,1))}
 try{enter();for(const item of rootOrder){const c=child(root,item.action),v=-negamax(c,delta(acc,c),depth-1,-Infinity,-value);if(v>value){value=v;best=item}}
 assert(best&&Number.isFinite(value));completed={completed_depth:depth,Action:best.Action,value};depths.push({...completed,status:'COMPLETED',wall_ms:now()-start,processed:stats.processed-before.processed,NN:stats.NN-before.NN,root_all_legal_count:legal.length,root_first:rootOrder[0].Action,selected_value_bound:'exact under this finite depth search; nonbest failsoft values may be upper bounds',all_exact_child_values:'NOT_RECORDED',equal_argmax_set:'NOT_RECORDED'});
 }catch(e){if(!['NODE_CAP','INTERNAL_DEADLINE','CANCELLED','GLOBAL_NN_CAP'].includes(e.message))throw e;typedStop=e.message;discard=depth;depths.push({requested_depth:depth,status:'INCOMPLETE',adopted:false,wall_ms:now()-start,processed:stats.processed-before.processed,NN:stats.NN-before.NN});break}
 }
 }catch(e){if(!['NODE_CAP','INTERNAL_DEADLINE','CANCELLED','GLOBAL_NN_CAP'].includes(e.message))throw e;typedStop=e.message;discard=1}
 assert.equal(root._positionKey(),key);assert.equal(n.history(root),history);
 return{status:completed?'COMPLETED_ACTION':'NO_COMPLETED_DEPTH',...completed,typed_stop:typedStop,partial_depth_discarded:discard,requested_depth:maxdepth,node_cap:cap,last_completed_only:true,action_legal:completed?legal.some(x=>x.Action===completed.Action):null,parent_copy_key_history_restored:true,stats,spans,wholewall_ms:now()-begin,map_delta:{hits:q.stats().hits-maps.hits,misses:q.stats().misses-maps.misses,current:q.stats().current},depths,root_key:key,root_history:history,TT:0,noise:0,policy_exclusion:false,ordering,nonbest_failsoft:'bounds; all exact children and equal argmax NOT_RECORDED',profile_limit:'inclusive overlapping intervals; not additive exclusive cost'};
}
module.exports={search,now,n,q};
