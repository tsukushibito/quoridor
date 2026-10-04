'use strict';
const fs=require('fs'),assert=require('assert'),n=require('./native.cjs'),{q}=n;
const {w,m}=n.load(process.argv[2]),clock=()=>Number(process.hrtime.bigint())/1e6;
let NN=0;const results=[];
function search(root,name){
 const start=clock(),key=root._positionKey(),hist=n.history(root);let stats={visited:0,processed:0,rejected_entry:0,NN:0,D_evals:0,terminal:0,full_accum:0,delta_accum:0,legal_calls:0,cutoffs:0},spans={terminal_ms:0,legal_and_order_ms:0,state_copy_next_ms:0,accum_input_ms:0,evaluator_ms:0};const mapBefore=q.stats();
 const measure=(kind,fn)=>{const st=clock(),v=fn();spans[kind]+=clock()-st;return v};
 function ordered(s){stats.legal_calls++;return measure('legal_and_order_ms',()=>s.getLegalActions().map(action=>({action,Action:q.r.rustAction(s,action)})).sort((a,b)=>a.Action-b.Action))}
 function term(s){return measure('terminal_ms',()=>q.r.terminalResult(s))}
 function next(s,action){return measure('state_copy_next_ms',()=>s.next(action))}
 function accum(parent,s){if(name!=='NNUE')return null;stats.delta_accum++;return measure('accum_input_ms',()=>q.delta(parent,s,w))}
 function leaf(s,a){return measure('evaluator_ms',()=>{if(name==='NNUE'){stats.NN++;NN++;assert(NN<=20000);return n.valueScaled(a,w,m)}stats.D_evals++;return n.distance(s,m)})}
 function enter(){stats.visited++;if(stats.processed>=2048){stats.rejected_entry++;throw Error('NODE_CAP')}stats.processed++}
 function negamax(s,a,depth,alpha,beta){enter();const terminal=term(s);if(terminal){stats.terminal++;return terminal.value}if(depth===0)return leaf(s,a);let v=-Infinity;for(const item of ordered(s)){const child=next(s,item.action);const cv=-negamax(child,accum(a,child),depth-1,-beta,-alpha);if(cv>v)v=cv;if(cv>alpha)alpha=cv;if(alpha>=beta){stats.cutoffs++;break}}assert(v!==-Infinity,'NOLEGAL_NONTERMINAL');return v}
 const terminal=term(root);assert(!terminal,'FIXTURE_ROOT_TERMINAL');const legal=ordered(root);assert(legal.length);
 const a=name==='NNUE'?measure('accum_input_ms',()=>{stats.full_accum++;return q.full(root,w)}):null;
 const bytes=a?a.a.map(v=>Buffer.from(v.buffer).toString('hex')):null;
 let completed=null,stop=null,discard=null;const depths=[];
 for(let depth=1;depth<=2;depth++){const before={...stats},ds=clock();let best=null,value=-Infinity;try{enter();for(const item of legal){const child=next(root,item.action),cv=-negamax(child,accum(a,child),depth-1,-Infinity,-value);if(cv>value){value=cv;best=item}}
  assert(best&&legal.some(k=>k.Action===best.Action));completed={completed_depth:depth,Action:best.Action,value};depths.push({...completed,wall_ms:clock()-ds,nodes_this_depth:stats.processed-before.processed,NN_this_depth:stats.NN-before.NN,root_all_actions:legal.length});
 }catch(e){if(e.message!=='NODE_CAP')throw e;stop=e.message;discard=depth;depths.push({requested_depth:depth,status:'INCOMPLETE',adopted:false,wall_ms:clock()-ds,nodes_this_depth:stats.processed-before.processed});break}}
 assert.equal(root._positionKey(),key);assert.equal(n.history(root),hist);if(a)assert.deepStrictEqual(a.a.map(v=>Buffer.from(v.buffer).toString('hex')),bytes);
 assert(completed&&completed.completed_depth>=1);
 return{name,...completed,requested_depth:2,node_cap:2048,typed_stop:stop,partial_depth_discarded:discard,last_completed_only:true,action_legal:true,parent_copy_restored:true,stats,spans,wholewall_ms:clock()-start,map_delta:{hits:q.stats().hits-mapBefore.hits,misses:q.stats().misses-mapBefore.misses,current:q.stats().current},depths,root_key:key,root_history:hist,all_legal_actions_in_completed_root_depth:true,TT:0,noise:0,policy_exclusion:false,order:'ascending real-board Rust Action; tie first strict greater',samewall_strength_claim:false};
}
const begin=clock();
for(const f of q.fixtures()){const NNUE=search(f.state,'NNUE'),distance=search(f.state,'distance');results.push({id:f.id,NNUE,distance,same_action:NNUE.Action===distance.Action});}
const result={UTC:new Date().toISOString(),samples:NN,roots:results,total_wholewall_ms:clock()-begin,profile_limit:'recorded spans overlap enclosing parent wall; terminal includes legal check; no sum advertised as wholewall',implementation:'Node native-hosted scaled QF1 vs train-fit distance; not Rust/Wasm',games4:{planned:4,status:'NOT_RUN',reason:'remaining frame and clock validation cost'},training:0,GPU:0,history_not_model_input:true,teacher_rootmean_not_minimax_leaf_truth:true,strength_claim:false};
fs.writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({samples:NN,wholewall_ms:result.total_wholewall_ms,roots:results.map(r=>({id:r.id,NNUE:r.NNUE.Action,D:r.distance.Action,NNUEdepth:r.NNUE.completed_depth,Ddepth:r.distance.completed_depth,NNUEstop:r.NNUE.typed_stop,Dstop:r.distance.typed_stop}))}));
