const fs=require('fs'),vm=require('vm'),crypto=require('crypto'),cp=require('child_process');
const D='research-data/ai-sigma/169-native-games-independent/',O='research-data/ai-sigma/165-native-baseline/',B='.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/runs/';
const read=p=>JSON.parse(fs.readFileSync(p)),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),check=(v,m)=>{if(!v)throw Error(m)};
const context=vm.createContext({Float32Array,Uint32Array,Uint8Array,Math,console});
for(const n of ['game.js','context.js'])vm.runInContext(cp.execFileSync('git',['show','19275b3:tools/ai-sigma-native-baseline/'+n],{encoding:'utf8'}),context);
vm.runInContext('globalThis.A={State,sameAction,rustAction,terminalResult}',context);const A=context.A,bits=v=>Array.from(new Uint32Array(Float32Array.from(v).buffer)),hist=s=>Array.from(s.position_history).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
const inputs=read(O+'stageB-inputs.json'),pre=read(O+'stageB-preregister.json');
const R={shared_RuleA:true,new_NN:0,owner_verdict_used:false,source:'19275b3',raw:[],games:[],pairs:[],roots:[],counts:{},clock:{public:[],cut:[],admit:[],receive:[],firstCP:[],cleanup:[],missing_actual_receipt:0,min_next_gate_gap:Infinity,min_402_recorded_margin:Infinity},cost:{games_ms:0,arena_ms:0,job_wall_ms:0,init_ms:0,journal_bytes:0,CP:0},science_stop_sha:sha(O+'science-stop.json'),input_sha:sha(O+'stageB-inputs.json')};
check(R.science_stop_sha==='9becd64e4bfac3e3d145765a7586b0e3376ac49aaae87d5b6ebdb7d49aac671c','stop hash');
for(let pair=1;pair<=8;pair++){
 const run=`native165-pair${String(pair).padStart(2,'0')}-r1`,dir=B+run+'/',raw=read(dir+'result.json'),rows=fs.readFileSync(dir+'journal.jsonl','utf8').trim().split('\n').map(JSON.parse);
 R.raw.push({run,sha:sha(dir+'result.json'),journal_sha:sha(dir+'journal.jsonl'),bytes:fs.statSync(dir+'result.json').size});R.cost.arena_ms+=raw.elapsed_ms;R.cost.journal_bytes+=fs.statSync(dir+'journal.jsonl').size;
 check(raw.planned===2&&raw.games.length===2&&raw.primary.length===0,'raw planned/error');check(rows.length===raw.public_hand_requests,'public denominator');let previous=null;
 for(const game of raw.games){
  const spec=inputs.games.find(x=>x.game_id===game.game_id),fixture=inputs.rows.find(x=>x.fixture?.id===game.fixture_id).fixture;check(spec&&eq(spec,{game_id:game.game_id,pair:game.pair,fixture_id:game.fixture_id,candidate_player:game.candidate_player,color_order:game.color_order}),'registered game');
  let s=new A.State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10});
  for(const a of fixture.legal_prefix){check(!A.terminalResult(s)&&s.getLegalActions().some(x=>A.sameAction(x,a)),'opening legal');s=s.next(a)}
  const legalids=()=>Array.from(s.getLegalActions(),a=>A.rustAction(s,a));
  check(s._positionKey()===fixture.root_state.key&&eq(hist(s),fixture.root_state.history)&&s.depth===fixture.target_ply,'opening state/history');check(eq(bits(s.toNNInput()),fixture.root_state.features_bits)&&eq(legalids(),fixture.root_state.legal),'opening bits/order');
  check(eq(game.legal_prefix.slice(0,fixture.target_ply),fixture.legal_prefix),'game prefix binding');const rr=rows.filter(x=>x.game_id===game.game_id);check(rr.length===game.plies_played,'game rows');
  const root=game.firstRoot;check(root.key===s._positionKey()&&root.side===s.getCurrentPlayer()&&eq(root.features_bits,bits(s.toNNInput()))&&root.NN_bits.length===137,'initial root bits/state');
  R.roots.push({game:game.game_id,pair,side:root.side,engine:root.engine,key:root.key,features_SHA:crypto.createHash('sha256').update(JSON.stringify(root.features_bits)).digest('hex'),NN_SHA:crypto.createHash('sha256').update(JSON.stringify(root.NN_bits)).digest('hex'),NN_bits:root.NN_bits,legal:legalids()});
  for(let i=0;i<rr.length;i++){
   const r=rr[i],pc=r.public_cp,p=pc.cp,act=game.legal_prefix[fixture.target_ply+i],ids=legalids();
   check(!A.terminalResult(s)&&r.key===s._positionKey()&&r.root_history_count===s.position_history.get(s._positionKey())&&r.ply===s.depth&&r.player===s.getCurrentPlayer(),'row state/history/side');check(r.engine===(r.player===game.candidate_player?'candidate':'reference'),'engine color');
   check(p.generation===r.generation&&ids.includes(p.action)&&s.getLegalActions().some(x=>A.sameAction(x,act))&&A.rustAction(s,act)===p.action,'public legal/generation');
   check(eq(p.root_edges.map(x=>x[0]),ids),'public full legal order');check(p.root_visits===p.simulations&&p.root_edges.reduce((n,e)=>n+e[2],0)===p.root_visits-1,'visits ledger');
   check(Math.abs(p.root_mean-p.root_valueSum/p.root_visits)<1e-12,'root mean');let best=p.root_edges[0];for(const e of p.root_edges)if(e[2]>best[2])best=e;check(best[0]===p.action,'first max visit action');
   check(pc.receive_ms>=0&&pc.admit_ms>=pc.receive_ms&&pc.admit_ms<=402&&r.public_actual_ms<=500&&pc.admit_ms<=r.public_actual_ms,'recorded clocks');check(r.zero&&r.zero.activeNN===0&&r.zero.handles===0&&r.zero.active===false&&!r.error,'quiescence/error');
   check(r.CP_received===r.CP_admitted+r.CP_late_discarded+r.CP_schema_rejected,'CP partition');check(r.CP_schema_rejected===0,'CP schema');
   const gate=pair===1?r.quiescent_receive_ms:r.quiescent_gate_observed_ms;if(pair===1)R.clock.missing_actual_receipt++;else check(r.quiescent_receive_ms!==null&&r.quiescent_receive_ms<=gate,'receipt/gate');
   if(previous){const gap=r.controller_t0_ms-(previous.controller_t0_ms+previous.gate);check(gap>=0,'next t0 after gate');R.clock.min_next_gate_gap=Math.min(R.clock.min_next_gate_gap,gap)}previous={controller_t0_ms:r.controller_t0_ms,gate};
   for(const [k,val]of Object.entries({public:r.public_actual_ms,cut:r.cut_actual_ms,admit:pc.admit_ms,receive:pc.receive_ms,firstCP:r.firstCP_ms,cleanup:r.cleanup_after_public_ms}))R.clock[k].push(val);R.clock.min_402_recorded_margin=Math.min(R.clock.min_402_recorded_margin,402-pc.admit_ms);
   const cnt=R.counts[r.engine]??=(Object.fromEntries(['starts','adoptedNN','adoptedBackup','completed','terminal_noNN','discard','CP_received','CP_admitted','CP_late','API_ms','pipe_ms','process_CPU_aux_ms'].map(k=>[k,0])));
   for(const[k,v]of Object.entries({starts:r.NN_calls,adoptedNN:p.nn_calls,adoptedBackup:p.root_visits,completed:r.completed,terminal_noNN:r.terminal_noNN,discard:r.NN_discarded,CP_received:r.CP_received,CP_admitted:r.CP_admitted,CP_late:r.CP_late_discarded,API_ms:r.API_total_ms,pipe_ms:r.NN_pipe_total_ms,process_CPU_aux_ms:r.NN_process_CPU_ms_aux}))cnt[k]+=v;
   check(r.completed===r.NN_calls-r.NN_discarded+r.terminal_noNN,'NN/backup partition');s=s.next(act);R.cost.CP+=r.CP_received;
  }
  const end=A.terminalResult(s);check(end&&end.winner===game.winner&&s.depth===game.final_ply&&s._positionKey()===game.final_key&&game.status==='GOAL'&&end.winner!==0,'final goal/winner');const score=end.winner===game.candidate_player?1:0;check(score===game.score,'score');
  R.games.push({game:game.game_id,pair,layer:fixture.target_ply,candidate_player:game.candidate_player,winner:end.winner,score,public:rr.length,final_ply:s.depth,elapsed_ms:game.elapsed_ms});R.cost.games_ms+=game.elapsed_ms;
 }
 const gg=R.games.filter(x=>x.pair===pair),roots=R.roots.filter(x=>x.pair===pair);check(eq(roots[0].NN_bits,roots[1].NN_bits)&&roots[0].features_SHA===roots[1].features_SHA&&eq(roots[0].legal,roots[1].legal),'paired initial root bits/order');R.pairs.push({pair,layer:gg[0].layer,Xi:gg.reduce((n,g)=>n+g.score,0)/2,same_board_side_winner:gg[0].winner===gg[1].winner,candidate_both_win:gg.every(g=>g.score===1),candidate_both_loss:gg.every(g=>g.score===0)});
}
R.WDL=[R.games.filter(g=>g.score===1).length,0,R.games.filter(g=>g.score===0).length];R.mean=R.games.reduce((n,g)=>n+g.score,0)/16;R.operational_identification=[R.mean,R.mean];R.terminal_quality_identification=[R.mean,R.mean];R.formal_clock_eligibility_unknown=true;R.formal_ready=false;R.layers=[12,13,24,25].map(layer=>({layer,games:R.games.filter(g=>g.layer===layer).length,score:R.games.filter(g=>g.layer===layer).reduce((n,g)=>n+g.score,0)/4}));
for(const key of ['public','cut','admit','receive','firstCP','cleanup']){const a=R.clock[key].sort((a,b)=>a-b);R.clock[key]={n:a.length,min:a[0],median:a[Math.floor(a.length/2)],p95:a[Math.floor(a.length*.95)],max:a[a.length-1],sum:a.reduce((n,x)=>n+x,0)}}
for(const r of R.roots)delete r.NN_bits;R.public=R.games.reduce((n,g)=>n+g.public,0);R.startup_NN=16;R.cost.games_per_second=16000/R.cost.games_ms;R.cost.arena_games_per_second=16000/R.cost.arena_ms;
fs.writeFileSync(D+'replay-result.json',JSON.stringify(R,null,2)+'\n');console.log(JSON.stringify(R));
