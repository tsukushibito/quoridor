'use strict';
importScripts('/player-base.js');
const portInherited=onmessage;let portTraceOn=false,portDeadline=null,portNumeric=[],portBackup=[],portSelections=[],portCPs=[],portIds=new WeakMap(),portNextId=0,portEvaluationNode=null;
function portId(n){if(!portIds.has(n))portIds.set(n,portNextId++);return portIds.get(n);}
function portPath(n){const actions=[];for(let c=n;c.parent;c=c.parent)actions.unshift(rustAction(c.parent.state,c.action));return actions;}
function portState(s){const f=s.toNNInput();return{key:s._positionKey(),history:[...s.position_history].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0),ply:s.depth,turn:s.isPlayer1Turn()?0:1,features_bits:Array.from(new Uint32Array(f.buffer,f.byteOffset,f.length)),legal:s.getLegalActions().map(a=>rustAction(s,a))};}
const portOrigExpand=expandNode;
expandNode=async function(n,e){if(portTraceOn){portId(n);portEvaluationNode=n;}try{const v=await portOrigExpand(n,e);if(portTraceOn)for(const c of n.children)portId(c);return v;}finally{portEvaluationNode=null;}};
const portOrigBest=MCTSNode.prototype.bestChild;
MCTSNode.prototype.bestChild=function(...args){const c=portOrigBest.apply(this,args);if(portTraceOn){let vs=0;for(const x of this.children)if(x.visitCount>0)vs+=x.basePrior;const q=c.visitCount===0?this.qValue-.2*Math.sqrt(vs):-c.qValue,u=c.prior*Math.sqrt(this.visitCount)/(1+c.visitCount);let root=this;while(root.parent)root=root.parent;portSelections.push({K_before:root.visitCount,path_before:portPath(this),node_index:portId(this),nodeN:this.visitCount,nodeSum:this.valueSum,parentQ:this.qValue,visited_base_prior_sum:vs,Action:rustAction(this.state,c.action),prior:c.prior,childN:c.visitCount,childSum:c.valueSum,childQ:c.qValue,score:q+u});}return c;};
const portOrigBackup=backup;
backup=function(n,v){let record;if(portTraceOn){const updates=[];let x=n,value=v;while(x){updates.push({index:portId(x),preN:x.visitCount,preSum:x.valueSum,value});value=-value;x=x.parent;}let root=n;while(root.parent)root=root.parent;record={K:root.visitCount+1,leaf_index:portId(n),path:portPath(n),value_leaf_side:v,terminal:terminalResult(n.state)?.value??null,updates};}portOrigBackup(n,v);if(record)portBackup.push(record);};
async function portSearch(d){
 if(active||activeNN||b.liveHandles()||d.engine!==boundEngine)throw Error('PORT_OLD_ZERO_OR_ROUTING');
 let state=fromPrefix(d.fixture.legal_prefix);if(terminalResult(state))throw Error('PORT_INPUT_TERMINAL');generation=d.generation;active=true;portDeadline=epoch()+d.timeout_ms;portTraceOn=true;portNumeric=[];portBackup=[];portSelections=[];portCPs=[];portIds=new WeakMap();portNextId=0;
 let cp=null,primary=null,handle=null,trace=null,root=null;const spans=[],originalInfer=b.infer,start=epoch();
 b.infer=async bits=>{if(epoch()>=portDeadline)throw Error('PORT_WATCHDOG');activeNN++;const t=epoch();try{const result=await originalInfer(bits);spans.push({start:t,end:epoch(),API_start:result.session_run_start_ms,API_end:result.session_run_end_ms});if(boundEngine==='reference'&&portEvaluationNode)portNumeric.push({...portState(portEvaluationNode.state),path:portPath(portEvaluationNode),node_index:portId(portEvaluationNode),policy_logits:result.logits,value:result.value});return result;}finally{activeNN--;}};
 try{
  if(boundEngine==='candidate'){
   let s=fromPrefix([]),prefix=[];for(const a of d.fixture.legal_prefix){prefix.push(rustAction(s,a));s=s.next(a);}
   handle=b.create({prefix,diagnostic:true,simulations:d.K,generation,seed:1979,trace:true,max_nodes:200000,max_depth:200});
   while(true){if(epoch()>=portDeadline)throw Error('PORT_WATCHDOG');const q=b.call({op:'begin',handle,generation});if(q.pending){const n=await b.infer(q.features_bits);portNumeric.push({...q,policy_logits:n.logits,value:n.value});b.call({op:'resume',handle,generation,token:q.token,logits:n.logits,value:n.value});}cp=b.call({op:'checkpoint',handle,generation});portCPs.push(cp);if(cp.simulations===d.K)break;if(cp.simulations>d.K)throw Error('K_OVERRUN');await yieldTask();}
   trace=b.call({op:'trace',handle,generation});cp=b.call({op:'snapshot',handle,generation});
  }else{
   const c={generation,cooperative:false,nnCalls:0,simulations:0,spans:[],steps:[],onComplete:n=>{portCPs.push({...referenceCP(n,{...c,nnCalls:spans.length},{generation}),root_mean:n.qValue,root_valueSum:n.valueSum});}};clockContext=c;
   root=await runMCTS(state,d.K-1,nnEvaluator,generation);cp={...referenceCP(root,{...c,nnCalls:spans.length},{generation}),root_mean:root.qValue,root_valueSum:root.valueSum};trace={selects:portSelections,backups:portBackup};
  }
 }catch(e){primary={name:e.name,message:e.message,stack:e.stack};}
 finally{if(handle!==null)b.free(handle);b.infer=originalInfer;clockContext=null;active=false;portTraceOn=false;portDeadline=null;send({kind:'port_result',id:d.id,engine:boundEngine,fixture_id:d.fixture.id,K:d.K,cp,CPs:portCPs,numeric:portNumeric,trace,spans,primary,zero:{handles:b.liveHandles(),activeNN,active},completed:boundEngine==='candidate'?cp?.simulations:root?.visitCount,terminal_noNN:(boundEngine==='candidate'?cp?.simulations:root?.visitCount)-spans.length,start_ms:start,end_ms:epoch()});}
}
onmessage=async e=>{if(e.data.kind!=='port_search')return portInherited(e);try{await portSearch(e.data);}catch(error){send({kind:'port_result',id:e.data.id,primary:{message:error.message},zero:{handles:b?.liveHandles(),activeNN,active}});}};
