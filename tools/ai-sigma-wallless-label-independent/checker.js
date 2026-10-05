'use strict';
const WL={active:false,started:0,completed:0};
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function need(c,m){if(!c)throw Error(m);}
function bounds(values,own){return [0,1].map(j=>values.reduce((x,v)=>own?Math.max(x,v[j]):Math.min(x,v[j]),own?-1:1));}
function result(s,me){const w=s.winner();return w?w===me?1:-1:s.isDrawn()?0:null;}
function policyId(a){if(a.type==='pawn')return [[0,1],[0,-1],[-1,0],[1,0],[-1,1],[1,1],[-1,-1],[1,-1]].findIndex(d=>equal(d,a.direction));return (a.orientation==='h'?8:72)+a.y*8+a.x;}
function hist(s){return [...s.position_history].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);}
function prefixIndependent(prefix){let state=new State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10});for(const a of prefix){need(result(state,1)===null,'TERMINAL_PREFIX');need(state.getLegalActions().some(b=>equal(a,b)),'PREFIX_ILLEGAL');state=state.next(a);}return state;}
function solver(root,limits){
 const me=root.getCurrentPlayer(),begin=performance.now(),proof=[],stack=[];let nodes=1,term=0,depthUnknown=0,nodeUnknown=0,timeUnknown=0,maxDepth=0;
 function push(state,p,a,d,forced=null){const id=proof.length;proof.push({p,a,s:state?state.getCurrentPlayer():null,i:[-1,1],r:forced,applied:!!state});stack.push({state,id,d,next:0,legal:null,children:[]});return id;}
 push(root,-1,null,0);
 while(stack.length){
  const frame=stack[stack.length-1],record=proof[frame.id];maxDepth=Math.max(maxDepth,frame.d);
  if(frame.legal===null){
   if(record.r){if(record.r==='node')nodeUnknown++;else timeUnknown++;stack.pop();continue;}
   const t=result(frame.state,me);
   if(t!==null){record.i=[t,t];record.r='terminal';term++;stack.pop();continue;}
   if(frame.d===limits.depth){record.r='depth';depthUnknown++;stack.pop();continue;}
   frame.legal=frame.state.getLegalActions();need(frame.legal.length>0,'EMPTY_UNCLASSIFIED');
  }
  if(frame.next<frame.legal.length){
   const a=frame.legal[frame.next++],cap=nodes>=limits.nodes?'node':performance.now()-begin>=limits.ms?'time':null;
   if(!cap)nodes++;
   const id=push(cap?null:frame.state.next(a),frame.id,policyId(a),frame.d+1,cap);frame.children.push(id);
  }else{record.i=bounds(frame.children.map(i=>proof[i].i),frame.state.getCurrentPlayer()===me);record.r=frame.state.getCurrentPlayer()===me?'max':'min';stack.pop();}
 }
 return {me,interval:proof[0].i,actions:proof.filter(p=>p.p===0).map(p=>({policy_index:p.a,interval:p.i})),nodes,terminal:term,depthUnknown,nodeUnknown,timeUnknown,maxDepth,wall_ms:performance.now()-begin,proof};
}
function proofCheck(root,label,limits){
 const rows=label.proof,children=rows.map(()=>[]),states=new Array(rows.length),depth=new Array(rows.length),actual=new Array(rows.length),me=root.getCurrentPlayer();let applied=0,term=0,unknown=0;
 need(rows.length>0&&rows[0][0]===-1&&rows[0][1]===null,'PROOF_ROOT');states[0]=root;depth[0]=0;
 rows.forEach((r,i)=>{need(r[3]>=-1&&r[4]<=1&&r[3]<=r[4],'BOUND_RANGE');if(i){need(Number.isInteger(r[0])&&r[0]>=0&&r[0]<i,'PARENT_ORDER');children[r[0]].push(i);}});
 for(let i=0;i<rows.length;i++){
  const r=rows[i];if(i){const p=r[0];need(states[p],'PLACEHOLDER_PARENT');const candidates=states[p].getLegalActions();const a=candidates.find(a=>policyId(a)===r[1]);need(!!a&&policyId(a)===actionToIndex(a,9),'EDGE_ACTION');depth[i]=depth[p]+1;if(r[6])states[i]=states[p].next(a);}
  if(!r[6]){need(!children[i].length&&equal(r.slice(3,5),[-1,1])&&['node','time'].includes(r[5]),'PLACEHOLDER_UNKNOWN');actual[i]=[-1,1];continue;}
  applied++;const s=states[i];need(s&&s.getCurrentPlayer()===r[2],'STATE_SIDE');const t=result(s,me);
  if(t!==null){term++;need(r[5]==='terminal'&&!children[i].length,'TERMINAL_REASON');actual[i]=[t,t];}
  else if(depth[i]===limits.depth){unknown++;need(r[5]==='depth'&&!children[i].length,'DEPTH_UNKNOWN');actual[i]=[-1,1];}
  else{need(depth[i]<limits.depth,'DEPTH_OVERRUN');const legal=s.getLegalActions();need(equal(children[i].map(j=>rows[j][1]),legal.map(policyId)),'EXHAUSTIVE_LEGAL_ORDER');need(r[5]===(s.getCurrentPlayer()===me?'max':'min'),'MAX_MIN_SIDE');}
 }
 for(let i=rows.length-1;i>=0;i--){if(!actual[i])actual[i]=bounds(children[i].map(j=>actual[j]),states[i].getCurrentPlayer()===me);need(equal(actual[i],rows[i].slice(3,5)),'INTERVAL_AGGREGATION');}
 need(applied<=limits.nodes&&applied===label.nodes&&term===label.terminalCount.win+label.terminalCount.loss+label.terminalCount.draw&&unknown===label.stops.depth,'COUNTS');
 const actions=children[0].map(j=>({policy_index:rows[j][1],interval:actual[j]}));need(equal(actions,label.actions.map(a=>({policy_index:a.action,interval:a.interval}))),'ROOT_ACTION_LABEL');
 return {nodes:applied,proof_rows:rows.length,terminal:term,depthUnknown:unknown,actions,interval:actual[0],all_parent_states_legal:true,algorithm:'forward state reconstruction, reverse interval aggregation'};
}
function mocks(){
 const passes=[];function test(c,n){need(c,'MOCK_'+n);passes.push(n);}
 test(equal(bounds([[1,1],[-1,-1]],true),[1,1]),'own_max');test(equal(bounds([[1,1],[-1,-1]],false),[-1,-1]),'opponent_min');test(equal(bounds([[-1,1],[1,1]],false),[-1,1]),'unknown_not_draw');
 test(result({winner:()=>1,isDrawn:()=>true},1)===1&&result({winner:()=>1,isDrawn:()=>true},2)===-1,'goal_before_draw_both_perspectives');test(result({winner:()=>0,isDrawn:()=>true},1)===0,'actual_draw_payoff');
 const pre=[];for(let i=0;i<7;i++)pre.push({type:'pawn',direction:[0,1]},{type:'pawn',direction:[i%2?-1:1,0]});const s=prefixIndependent(pre);const a=s.getLegalActions().find(a=>equal(a,{type:'pawn',direction:[0,1]}));test(!!a&&result(s.next(a),1)===1&&result(s.next(a),2)===-1,'RuleA_goal_both_perspectives');test(s.getLegalActions().every(a=>policyId(a)===actionToIndex(a,9)),'actual_action_indices');
 return {passes,shared_RuleA:true,small_only:true};
}
function validateInput(input,reg,k){
 const s=prefixIndependent(input.prefix),cfg=reg.cases[k],target=k?[[4,5],[4,2]]:[[4,6],[3,3]];
 need(input.attempt===0&&input.seed===cfg.seed&&!input.error,'FIRST_ATTEMPT');need(s.depth===(k?33:32)&&input.prefix.length===s.depth&&s.getCurrentPlayer()===cfg.side&&s.walls_p1===0&&s.walls_p2===0&&result(s,cfg.side)===null,'REGISTERED_STATE');need(equal([s.player1pos,s.player2pos],target)&&equal(target,input.pawns),'TARGET_PAWNS');
 let seed=cfg.seed>>>0;const shuffle=[];for(const x of [0,1,2,6,7])for(const y of [0,2,4,6])shuffle.push({type:'wall',x,y,orientation:'v'});
 for(let i=19;i>0;i--){seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;const j=(seed>>>0)%(i+1);[shuffle[i],shuffle[j]]=[shuffle[j],shuffle[i]];}
 need(equal(shuffle,input.prefix.slice(0,20)),'PREREGISTER_WALL_ORDER');
 const pawn=[];for(let i=0;i<6;i++)pawn.push({type:'pawn',direction:k&&i===0?[1,0]:[0,1]},{type:'pawn',direction:!k&&i===0?[-1,0]:[0,-1]});if(k)pawn.push({type:'pawn',direction:[-1,0]});need(equal(pawn,input.prefix.slice(20)),'PREREGISTER_PAWN_SCRIPT');
 const h=[...input.history].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);need(s._positionKey()===input.key&&equal(hist(s),h),'KEY_HISTORY');const f=s.toNNInput();need(f.length===648&&equal(Array.from(new Uint32Array(f.buffer)),input.featuresbits),'FEATURE648');
 const legal=s.getLegalActions();need(legal.length===4&&equal(legal,input.root_legal)&&legal.every(a=>policyId(a)===actionToIndex(a,9)),'ROOT_OBJECTS_ORDER_INDICES');
 return {s,summary:{id:cfg.id,side:s.getCurrentPlayer(),prefix:s.depth,pawns:target,walls:[0,0],key:s._positionKey(),features:648,root_actions:legal.map(a=>({object:a,policy_index:policyId(a),rust209_action:rustAction(s,a)})),fixed_golden:false}};
}
let pendingCases=[];const startedCases=new Set();
function preflight(inputText){
 const input=JSON.parse(inputText),reg=input.reg,out={mocks:mocks(),cases:[],NN:0,model_load:0,AIWorker:0,shared_RuleA_independence_limit:true};need(reg.depth===6&&reg.applied_node_cap===20000&&reg.watchdog_ms===20000,'FIXED_LIMITS');
 for(let k=0;k<2;k++){
  const {s,summary}=validateInput(input.samples[k].generation.adopted,reg,k),limits={depth:6,nodes:20000,ms:20000};const saved=proofCheck(s,input.samples[k].label,limits);
  pendingCases.push({s,summary,saved,limits});out.cases.push({input:summary,saved_proof:saved,immediate_goals:s.getLegalActions().filter(a=>result(s.next(a),s.getCurrentPlayer())===1).map(policyId)});
 }
 return {...out,main_active:WL.active,solver_started:WL.started,solver_completed:WL.completed};
}
function executeCase(k){need(!startedCases.has(k),'SUCCESS_OR_ATTEMPT_REPETITION');startedCases.add(k);const p=pendingCases[k];WL.active=true;WL.started++;try{const fresh=solver(p.s,p.limits);WL.completed++;return {input:p.summary,independent:fresh,root_intervals_equal:equal(fresh.actions,p.saved.actions)&&equal(fresh.interval,p.saved.interval)};}finally{WL.active=false;}}
