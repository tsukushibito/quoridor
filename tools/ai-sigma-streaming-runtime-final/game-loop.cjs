const J=require('./judge.cjs');
function terminalScore(t,candidateColor){return (t.winner==null||t.winner===0)?.5:t.winner===candidateColor?1:0;}
const {classifyFailure}=require('./failures.cjs');
async function runGame({prefix,candidateColor,platform,choose,log=()=>{},maxAddedPly=Infinity,clock=require('./transaction.cjs').now}){
 const initial=JSON.parse(JSON.stringify(prefix));J.ids(initial);if(J.terminalResult(J.state(initial)))throw Error('TERMINAL_INITIAL_PREFIX');
 let current=initial;
 for(let added=0;;added++){
  const state=J.state(current),terminal=J.terminalResult(state);
  if(terminal)return {complete:true,terminal,score:terminalScore(terminal,candidateColor),prefix:current};
  if(added>=maxAddedPly)return {complete:false,diagnostic_stop:true,prefix:current,outcome_unobserved:true};
  const color=state.getCurrentPlayer(),engine=color===candidateColor?(platform==='native-local'?'native':'candidate'):'reference';
  const response=await choose(engine,{id:'game-hand-'+current.length,legal_prefix:current});
  log({ply:current.length,color,engine,prefix:current,response});
  if(response.accepted!==true){const f=classifyFailure(response.engine===engine&&typeof response.accepted==='boolean'?response:{...response,error:"IDENTITY_MISMATCH"});return {...f,complete:f.kind==='engine_loss',score:f.kind==='engine_loss'?(color===candidateColor?0:1):null,responsible_engine:engine,prefix:current};}
  let action;try{action=J.validate(current,response.action)}catch(e){return {kind:'engine_loss',complete:true,score:color===candidateColor?0:1,reason:'illegal_action',prefix:current};}
  const encoded=JSON.parse(JSON.stringify(action));if(!Number.isFinite(response.t0_ms)||!Number.isFinite(response.T_ms))return {kind:'invalid_pair',complete:false,score:null,reason:'CLOCK_IDENTITY_MISSING',prefix:current};if(clock()>=response.t0_ms+response.T_ms)return {kind:'engine_loss',complete:true,score:color===candidateColor?0:1,reason:'LATE_CALLER_VALIDATION',responsible_engine:engine,prefix:current};current=[...current,encoded];
 }
}
async function runPair({prefix,colorOrder,play,correct,retryBudget}){
 for(let attempt=0;attempt<2;attempt++){
  const games=[];for(const color of colorOrder){const game=await play(JSON.parse(JSON.stringify(prefix)),color,attempt);games.push(game);if(game.kind==='invalid_pair'||!game.complete)break;}
  if(games.length===2&&games.every(g=>g.complete&&g.kind!=='invalid_pair'))return {complete:true,games,Xi:games.reduce((s,g)=>s+g.score,0)/2,attempt};
  if(games.some(g=>g.kind==='invalid_pair')&&attempt===0&&retryBudget.remaining>0){retryBudget.remaining--;await correct();continue;}
  return {complete:false,games,attempt,reason:'invalid or incomplete pair; no replacement prefix'};
 }
}
module.exports={runGame,runPair,classifyFailure,terminalScore};
