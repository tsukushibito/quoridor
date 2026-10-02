function certify(s, cap=20000) {
 const me=s.getCurrentPlayer(), legal=s.getLegalActions(), wins=[], branches=[];let nodes=1,limited=false;
 const take=()=>{if(nodes>=cap){limited=true;return false;}nodes++;return true;};
 for(const a of legal){if(!take())break;const n=s.next(a);branches.push({action:a,state:n});if(n.winner()===me)wins.push(a);}
 const rootComplete=branches.length===legal.length;
 const result={root_key:s._positionKey(),player:me,root_legal:legal,root_legal_count:legal.length,immediate_wins:wins,immediate_wins_complete:rootComplete,nodes,cap,opponent_immediate_possible:[],next_ply_loss_avoid:[],unresolved_root_actions:[],next_ply_labels_complete:false,longterm_result:'UNDETERMINED'};
 if(!rootComplete){result.unresolved_root_actions=legal.slice(branches.length);result.reason='NODE_CAP_ROOT';return result;}
 if(wins.length){result.reason='IMMEDIATE_GOAL_PRIORITY_DEPTH2_NOT_REQUESTED';return result;}
 for(let i=0;i<branches.length;i++){
  const b=branches[i],n=b.state;
  if(n.winner()||n.depth>=200){result.next_ply_loss_avoid.push(b.action);continue;}
  const replies=n.getLegalActions(),winning=[];let complete=true;
  for(const a of replies){if(!take()){complete=false;break;}if(n.next(a).winner()===3-me)winning.push(a);}
  if(winning.length)result.opponent_immediate_possible.push({action:b.action,winning_replies:winning,replies_complete:complete});
  if(!complete){result.unresolved_root_actions.push(b.action,...branches.slice(i+1).map(x=>x.action));break;}
  if(!winning.length)result.next_ply_loss_avoid.push(b.action);
 }
 result.nodes=nodes;result.next_ply_labels_complete=!limited;result.reason=limited?'NODE_CAP_OPPONENT':'COMPLETE_DEPTH2';return result;
}
function oracleRun(reg) {
 const attempts=[],inputs=[],labels=[];
 const pawn=(x,y)=>({type:'pawn',direction:[x,y]}),wall=(x,y)=>({type:'wall',x,y,orientation:'h'});
 function make(index,attempt){let s=new State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10}),prefix=[];
  function apply(a){if(terminalResult(s))throw Error('PREMATURE_TERMINAL');if(!s.getLegalActions().some(b=>sameAction(a,b)))throw Error('ILLEGAL_GENERATED_STEP');s=s.next(a);prefix.push(a);}
  function leftStay(player){const pos=player===1?s.player1pos:s.player2pos;return pawn(pos[0]>attempt%2?-1:1,0);}
  if(index===3){apply(wall(3,0));apply(wall(0,6));}
  if(index===2){apply(pawn(-1,0));apply(pawn(1,0));for(let k=0;k<7;k++){apply(pawn(0,1));apply(pawn(0,-1));}}
  else for(let k=0;k<7;k++){apply(index===0?pawn(0,1):leftStay(1));apply(index===0?leftStay(2):pawn(0,-1));}
  const fits=s.getCurrentPlayer()===1&&!terminalResult(s)&&(index===0?s.player1pos[1]===7&&s.player2pos[1]===8:index===2?s.player1pos[1]===7&&s.player2pos[1]===1:s.player1pos[1]===0&&s.player2pos[1]===1);
  if(!fits)throw Error('GEOMETRY_NOT_REACHED');return {s,prefix};
 }
 for(let i=0;i<reg.cases.length;i++){
  let generated=null;
  for(let a=0;a<reg.attempt_limit;a++){
   try{generated=make(i,a);attempts.push({case:reg.cases[i].id,attempt:a,accepted:true,prefix:generated.prefix,key:generated.s._positionKey()});break;}
   catch(e){attempts.push({case:reg.cases[i].id,attempt:a,accepted:false,error:e.message});}
  }
  if(!generated){labels.push({case:reg.cases[i].id,status:'NOT_GENERATED'});continue;}
  const {s,prefix}=generated;inputs.push({case:reg.cases[i].id,legal_prefix:prefix,key:s._positionKey(),history:Array.from(s.position_history),player:s.getCurrentPlayer(),depth:s.depth,pawns:[s.player1pos,s.player2pos],walls_remaining:[s.walls_p1,s.walls_p2],H:Array.from(s.hwall_anchors),V:Array.from(s.vwall_anchors)});
  const certificate=certify(s,reg.nodes_cap??20000);labels.push({case:reg.cases[i].id,certificate});
 }
 const tests=[];
 if(inputs.length){const s=fromPrefix(inputs[0].legal_prefix),c=certify(s,1);if(c.immediate_wins_complete||c.next_ply_labels_complete||c.next_ply_loss_avoid.length)throw Error('CAP_MOCK_FALSE_SAFE');tests.push({kind:'cap1',passed:true,reason:c.reason});}
 const own=labels.find(x=>x.case==='own-near-goal')?.certificate;if(own){if(!own.immediate_wins.length)throw Error('GOAL_MOCK_FAILED');tests.push({kind:'legal_immediate_goal',passed:true});}
 const threat=labels.find(x=>x.case==='opponent-threat')?.certificate;if(threat){if(!threat.opponent_immediate_possible.length||!threat.next_ply_loss_avoid.length)throw Error('THREAT_MOCK_FAILED');tests.push({kind:'legal_goal_threat_and_defence',passed:true});}
 return {issue:'quoridor-4lc.127',attempts,inputs,labels,tests,NN:0,models:0,AI_workers:0,games:0,limits:'depth2 finite sharedRuleA; not independent rule implementation',timers:0};
}
