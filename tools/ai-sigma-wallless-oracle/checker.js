'use strict';
function intervalOracle(root,me,api,limits){
 let nodes=1,terminalCount={win:0,loss:0,draw:0},maxPly=0,stops={},proof=[];const start=performance.now();
 const hit=r=>{stops[r]=(stops[r]||0)+1;};
 function visit(s,parent,action,ply,applied=true,forced=null){
  const id=proof.length,side=s?api.side(s):null,row=[parent,action,side,-1,1,'',applied?1:0];proof.push(row);maxPly=Math.max(maxPly,ply);
  if(forced){row[5]=forced;hit(forced);return id;}
  const t=api.terminal(s,me);
  if(t!==null){row[3]=row[4]=t;row[5]='terminal';terminalCount[t===1?'win':t===-1?'loss':'draw']++;return id;}
  if(ply>=limits.depth){row[5]='depth';hit('depth');return id;}
  const legal=api.legal(s);if(!legal.length)throw Error('UNCLASSIFIED_EMPTY_LEGAL');
  const children=[];
  for(const a of legal){
   let reason=nodes>=limits.nodes?'node':performance.now()-start>=limits.ms?'time':null;
   if(reason)children.push(visit(null,id,api.index(a),ply+1,false,reason));
   else {nodes++;children.push(visit(api.next(s,a),id,api.index(a),ply+1));}
  }
  const op=side===me?Math.max:Math.min;
  row[3]=op(...children.map(i=>proof[i][3]));row[4]=op(...children.map(i=>proof[i][4]));row[5]=side===me?'max':'min';return id;
 }
 visit(root,-1,null,0);
 const actions=proof.map((x,i)=>({row:x,i})).filter(x=>x.row[0]===0).map(({row,i})=>({action:row[1],interval:row.slice(3,5),proof_node:i}));
 return {root_player:me,interval:proof[0].slice(3,5),actions,nodes,proof_rows:proof.length,proof,terminalCount,maxPly,stops,wall_ms:performance.now()-start,limits,cache:false,pruning:false};
}
function abstractMocks(){
 const api={side:s=>s.side,terminal:s=>s.t??null,legal:s=>s.c||[],index:a=>a.id,next:(s,a)=>a.s};
 const terminal=t=>({side:2,t}),root={side:1,c:[{id:0,s:terminal(1)},{id:1,s:terminal(-1)}]};
 const run=(s,l={depth:6,nodes:20000,ms:20000})=>intervalOracle(s,1,api,l);
 const results=[];function check(name,condition){if(!condition)throw Error('MOCK_'+name);results.push(name);}
 check('max',JSON.stringify(run(root).interval)==='[1,1]');
 check('min',JSON.stringify(run({...root,side:2}).interval)==='[-1,-1]');
 check('draw',JSON.stringify(run(terminal(0)).interval)==='[0,0]');
 check('terminal_before_depth',JSON.stringify(run(terminal(-1),{depth:0,nodes:1,ms:0}).interval)==='[-1,-1]');
 for(const [name,l] of [['depth',{depth:0,nodes:20,ms:20}],['node',{depth:6,nodes:1,ms:20}],['time',{depth:6,nodes:20,ms:0}]])check(name,JSON.stringify(run(root,l).interval)==='[-1,1]');
 const mixed={side:2,c:[{id:0,s:terminal(1)},{id:1,s:{side:1,c:root.c}}]};check('unknown_min',JSON.stringify(run(mixed,{depth:1,nodes:20,ms:20}).interval)==='[-1,1]');
 check('no_history_cache',run(root).cache===false);
 return {artificial:true,pass:results};
}
function browserMocks(){
 const r=abstractMocks(),pawn=(x,y)=>({type:'pawn',direction:[x,y]});let s=fromPrefix([]),p=[];
 function take(a){if(!s.getLegalActions().some(b=>sameAction(a,b)))throw Error('MOCK_ILLEGAL');s=s.next(a);p.push(a);}
 for(let i=0;i<3;i++){take(pawn(0,1));take(pawn(0,-1));}take(pawn(0,1));take(pawn(0,-1));
 if(JSON.stringify(s.player2pos)!=='[4,3]')throw Error('MOCK_JUMP');
 let near=fromPrefix([]),hist=[];for(let i=0;i<7;i++){hist.push(pawn(0,1));hist.push(pawn(i%2===0?-1:1,0));}near=fromPrefix(hist);
 if(near.winner()!==0)throw Error('MOCK_NEAR_TERMINAL');const a=pawn(0,1);if(!near.getLegalActions().some(b=>sameAction(a,b))||near.next(a).winner()!==1)throw Error('MOCK_GOAL');
 const wall=(x,y)=>({type:'wall',x,y,orientation:'h'});const dh=[];for(let i=0;i<3;i++)dh.push(pawn(0,1),pawn(0,-1));dh.push(pawn(0,1),wall(4,5));const ds=fromPrefix(dh),diag=pawn(-1,1);if(!ds.getLegalActions().some(a=>sameAction(a,diag))||JSON.stringify(ds.next(diag).player1pos)!=='[3,5]')throw Error('MOCK_DIAGONAL');return {...r,ruleA_legal_jump_prefix:p,ruleA_neargoal_prefix:hist,ruleA_diagonal_prefix:dh,ruleA_pass:['jump','diagonal','goal_priority'],history_cache:'disabled',shared_rule_limit:true};
}
function walllessGenerate(reg,index){
 const c=reg.cases[index],attempts=[],pawn=(x,y)=>({type:'pawn',direction:[x,y]});let adopted=null;
 for(let attempt=0;attempt<reg.attempt_limit;attempt++){
  let s=fromPrefix([]),prefix=[],error=null;
  function take(a){if(prefix.length>=reg.prefix_cap)throw Error('PREFIX_CAP');if(terminalResult(s))throw Error('PREMATURE_TERMINAL');if(!s.getLegalActions().some(b=>sameAction(a,b)))throw Error('ILLEGAL_GENERATED_STEP');s=s.next(a);prefix.push(a);}
  try{
   let rng=(c.seed+attempt)>>>0;const rand=()=>{rng^=rng<<13;rng^=rng>>>17;rng^=rng<<5;return rng>>>0;};let walls=[];
   for(const x of [0,1,2,6,7])for(const y of [0,2,4,6])walls.push({type:'wall',x,y,orientation:'v'});
   for(let i=walls.length-1;i>0;i--){let j=rand()%(i+1);[walls[i],walls[j]]=[walls[j],walls[i]];}
   for(const a of walls)take(a);
   for(let i=0;i<6;i++){
    take(index===1&&i===0?pawn(1,0):pawn(0,1));
    take(index===0&&i===0?pawn(-1,0):pawn(0,-1));
   }
   if(index===1)take(pawn(-1,0));
   const target=index===0?[[4,6],[3,3]]:[[4,5],[4,2]];
   if(s.walls_p1!==0||s.walls_p2!==0||s.getCurrentPlayer()!==c.side||terminalResult(s)||JSON.stringify([s.player1pos,s.player2pos])!==JSON.stringify(target)||s.getLegalActions().length<2)throw Error('TARGET_MISSING');
  }catch(e){error={name:e.name,message:e.message};}
  const record={case:c.id,attempt,seed:c.seed+attempt,prefix,error,key:s._positionKey(),side:s.getCurrentPlayer(),pawns:[s.player1pos,s.player2pos],walls:[s.walls_p1,s.walls_p2],depth:s.depth,history:Array.from(s.position_history),board:{h:Array.from(s.hwalls),v:Array.from(s.vwalls),h_anchors:Array.from(s.hwall_anchors),v_anchors:Array.from(s.vwall_anchors)}};
  attempts.push(record);if(!error){const f=s.toNNInput();adopted={...record,featuresbits:Array.from(new Uint32Array(f.buffer,f.byteOffset,f.length)),root_legal:s.getLegalActions()};break;}
 }
 return {case:c.id,attempts,adopted};
}
function walllessCertify(input,reg){
 if(!input)return null;const s=fromPrefix(input.prefix),me=s.getCurrentPlayer();
 if(s._positionKey()!==input.key||s.walls_p1||s.walls_p2)throw Error('INPUT_BINDING');
 const api={side:s=>s.getCurrentPlayer(),terminal:(s,me)=>{const w=s.winner();if(w)return w===me?1:-1;if(s.isDrawn())return 0;return null;},legal:s=>s.getLegalActions(),index:a=>actionToIndex(a,9),next:(s,a)=>s.next(a)};
 const r=intervalOracle(s,me,api,{depth:reg.depth,nodes:reg.applied_node_cap,ms:reg.watchdog_ms});
 r.immediate_goals=s.getLegalActions().filter(a=>s.next(a).winner()===me).map(a=>actionToIndex(a,9));
 const exact=r.actions.filter(a=>a.interval[0]===a.interval[1]);
 r.classification=r.immediate_goals.length?'trivial-immediate':new Set(exact.map(a=>a.interval[0])).size>1?'nontrivial-certified-distinct':'limited-no-certified-distinction';
 r.all_root_actions_recorded=r.actions.length===s.getLegalActions().length;return r;
}
function verifyCertificate(input,label,reg){
 const root=fromPrefix(input.prefix),rows=label.proof;let applied=0,terminal=0,depthUnknown=0;
 const children=new Map();rows.forEach((r,i)=>{if(r[0]>=0){if(!children.has(r[0]))children.set(r[0],[]);children.get(r[0]).push(i);}});
 function walk(i,s,ply){
  const r=rows[i];if(r[3]<-1||r[4]>1||r[3]>r[4])throw Error('PROOF_INTERVAL');
  if(!r[6]){if(r[3]!==-1||r[4]!==1||!['node','time'].includes(r[5])||(children.get(i)||[]).length)throw Error('PROOF_PLACEHOLDER');return;}
  applied++;if(r[2]!==s.getCurrentPlayer())throw Error('PROOF_SIDE');
  const w=s.winner(),t=w?(w===label.root_player?1:-1):s.isDrawn()?0:null;
  if(t!==null){terminal++;if(r[5]!=='terminal'||r[3]!==t||r[4]!==t||(children.get(i)||[]).length)throw Error('PROOF_TERMINAL');return;}
  if(ply===reg.depth){depthUnknown++;if(r[5]!=='depth'||r[3]!==-1||r[4]!==1||(children.get(i)||[]).length)throw Error('PROOF_DEPTH');return;}
  const legal=s.getLegalActions(),ids=children.get(i)||[];
  if(ids.length!==legal.length)throw Error('PROOF_COMPLETENESS');
  for(let j=0;j<legal.length;j++){if(rows[ids[j]][1]!==actionToIndex(legal[j],9))throw Error('PROOF_LEGAL_ORDER');walk(ids[j],rows[ids[j]][6]?s.next(legal[j]):null,ply+1);}
  const own=s.getCurrentPlayer()===label.root_player,op=own?Math.max:Math.min;
  if(r[5]!== (own?'max':'min')||r[3]!==op(...ids.map(j=>rows[j][3]))||r[4]!==op(...ids.map(j=>rows[j][4])))throw Error('PROOF_PROPAGATION');
 }
 if(rows[0][0]!==-1||rows[0][1]!==null)throw Error('PROOF_ROOT');walk(0,root,0);
 if(applied!==label.nodes||applied>reg.applied_node_cap)throw Error('PROOF_NODE_COUNT');
 return {pass:true,applied,terminal,depthUnknown,root_action_count:(children.get(0)||[]).length,rule_implementation_shared:true,independent_aggregation_algorithm:true};
}
