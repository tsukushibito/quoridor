const fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const D='research-data/ai-sigma/155-sigma-web-port-games-independent/',O='research-data/ai-sigma/151-sigma-web-port/',B='.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs/';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'),eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b),check=(v,m)=>{if(!v)throw Error(m)};
const c=vm.createContext({Float32Array,Uint32Array,Uint8Array,Math,console});
for(const n of ['game.js','context.js'])vm.runInContext(fs.readFileSync('tools/ai-sigma-actual-boundary-repair/'+n,'utf8'),c);
vm.runInContext('globalThis.A={State,sameAction,rustAction,terminalResult,actionToIndex}',c);const A=c.A;
const hist=s=>Array.from(s.position_history).sort((a,b)=>a[0].localeCompare(b[0]));
const bits=v=>Array.from(new Uint32Array(Float32Array.from(v).buffer));
const inputs=read(O+'stageB-inputs.json'),pre=read(O+'stageB-preregister.json');
let result={shared_RuleA:true,owner_checker_called:false,games:[],roots:[],rows:0,clocks:[],counts:{candidate:{API:0,adoptedNN:0,backup:0,noNN:0,returned_discard:0},reference:{API:0,adoptedNN:0,backup:0,noNN:0,returned_discard:0}},sources:{},input_sha:sha(O+'stageB-inputs.json'),results_sha:sha(O+'stageB-results.json')};
let seen=new Set();
for(let g=1;g<=4;g++){
 const dir=B+`port151-stageB-group${g}-r1/`,config=read(dir+'config.json');
 check(config.fixed_input_SHA256===result.input_sha,'input binding');check(config.games.length===4,'group denominator');
 for(const spec of config.games){
 const path=dir+'completed-game-'+spec.id+'.json',raw=read(path),game=raw.game,rows=raw.rows;
 const fixed=pre.games.find(x=>x.id===game.id),fixture=inputs.prefixes.find(x=>x.fixture.id===game.fixture_id).fixture;
 check(fixed&&!seen.has(game.id),'fixed game');seen.add(game.id);check(eq(game.initial_prefix,fixture.legal_prefix),'prefix');check(game.candidate_color===fixed.candidate_color,'color');check(game.seed===1979,'search seed');
 let s=new A.State({boardsize:9,walls_p1:10,walls_p2:10,walls_initial:10});
 for(const a of game.initial_prefix){check(!A.terminalResult(s)&&s.getLegalActions().some(x=>A.sameAction(x,a)),'prefix legality');s=s.next(a)}
 check(s._positionKey()===fixture.history_count_key&&eq(hist(s),fixture.history_counts)&&s.getCurrentPlayer()===fixture.player,'fixture state');check(eq(bits(s.toNNInput()),fixture.features_bits),'fixture features');check(eq(Array.from(s.getLegalActions(),a=>A.rustAction(s,a)),fixture.legal_ids),'fixture legal order');
 check(game.actions.length===rows.length,'journal length');let previous={};let first=true;
 for(let i=0;i<rows.length;i++){
 const r=rows[i],id=r.identity,res=r.response,body=res.body,d=r.diagnostic,cp=r.adoptedCP,action=game.actions[i],t=id.t0_ms;
 check(!A.terminalResult(s),'postterminal action');check(id.key===s._positionKey()&&eq(id.history,hist(s)),'row state/history');check(eq(id.legal_prefix,[...game.initial_prefix,...game.actions.slice(0,i)]),'row prefix');check(id.engine===(s.getCurrentPlayer()===game.candidate_color?'candidate':'reference'),'engine side');
 check(s.getLegalActions().some(x=>A.sameAction(x,action))&&A.sameAction(action,body.action),'public action');check(body.generation===id.generation&&body.request_id===id.request_id,'generation');check(JSON.parse(res.body_serialized).request_id===id.request_id&&eq(JSON.parse(res.body_serialized),body),'body immutable');
 check(id.deadline_ms-t===500&&id.commit_cutoff_ms-t===402&&res.planned_ms-t===411,'budget');check(res.stamp_ms<=id.deadline_ms&&!body.cancelled&&!body.late&&!body.judge_error&&!body.external_abort,'public classification');
 const pub=d.sab_publications.find(x=>x.sequence===body.sequence);check(pub&&pub.sequence===cp.sequence&&pub.action===cp.action&&cp.action===A.rustAction(s,action),'adopted CP');
 const w=r.worker_clock;check(w.measured,'clock missing');let offsets=w.samples.map(x=>[x.start_ms-x.worker_ms-.1,x.end_ms-x.worker_ms+.1]); // actual raw bracket below; allowance handled separately
 const maxlo=Math.max(...w.samples.map(x=>x.worker_ms-x.end_ms)),minhi=Math.min(...w.samples.map(x=>x.worker_ms-x.start_ms));
 check(Math.abs(w.lo_ms-(maxlo-.1))<.001&&Math.abs(w.hi_ms-(minhi+.1))<.001,'clock bounds');
 check(pub.validation_end_ms-w.lo_ms<=id.commit_cutoff_ms,'CP cutoff');check(pub.begin_ms<=pub.validation_end_ms,'CP order');
 const st=r.stop;check(st&&st.stop.activeNN===0&&st.stop.live_searches===0&&st.stop.handles===0,'stop NN/search');check(st.main_received_ms>=res.stamp_ms,'ACK after public');
 if(previous[id.engine])check(r.own_previous_wait.end_ms>=previous[id.engine].stop.main_received_ms,'own reclaim');
 const opp=previous[id.engine==='candidate'?'reference':'candidate'];
 const cnt=result.counts[id.engine];cnt.API+=d.NN_control_events.length;cnt.adoptedNN+=cp.completed_NN;cnt.backup+=cp.completed_backup;cnt.noNN+=cp.completed_backup-cp.completed_NN;cnt.returned_discard+=d.NN_control_events.filter(x=>x.result_discarded).length;
 check(d.NN_control_events.length===r.hand_NN,'API count');check(cp.root_visits===cp.completed_backup&&cp.completed_NN<=cp.completed_backup,'backup count');
 result.clocks.push({id:id.request_id,engine:id.engine,elapsed:res.stamp_ms-t,cutoffMargin:id.commit_cutoff_ms-pub.validation_end_ms+w.lo_ms,ACK_ms:st.main_received_ms-t,other_t0_before_ACK:opp?t<opp.stop.main_received_ms:null,own_wait:r.own_previous_wait.wait_ms,root:cp.root_visits,edge:cp.root_visits-1,NN:cp.completed_NN,NN_discard:d.NN_control_events.filter(x=>x.result_discarded).length});
 if(first){
 const n=d.numeric[0];check(n&&eq(n.features_bits,bits(s.toNNInput())),'first NN features');
 result.roots.push({pair:fixed.pair,engine:id.engine,color:game.candidate_color,side:s.getCurrentPlayer(),key:id.key,history:id.history,features_bits:n.features_bits,numeric:n,legal:Array.from(s.getLegalActions(),a=>A.rustAction(s,a))});first=false;
 }
 previous[id.engine]=r;s=s.next(action);result.rows++;
 }
 const end=A.terminalResult(s);check(end&&end.winner===game.winner&&s.depth===game.total_ply&&s._positionKey()===game.final_key,'terminal winner/state');check(game.status==='terminal'&&game.reason===(end.winner?'goal':'draw'),'terminal classification');
 result.games.push({id:game.id,pair:fixed.pair,layer:fixed.layer_ply,color:game.candidate_color,winner:end.winner,score:end.winner===0?.5:end.winner===game.candidate_color?1:0,public:rows.length,totalply:s.depth,journal_sha:sha(path),reason:game.reason});
 }
}
check(seen.size===16,'16 planned');result.pairs=[];
for(let p=1;p<=8;p++){const games=result.games.filter(x=>x.pair===p);check(games.length===2,'pair count');const roots=result.roots.filter(x=>x.pair===p);check(roots.length===2,'root count');check(eq(roots[0].features_bits,roots[1].features_bits)&&eq(roots[0].history,roots[1].history)&&eq(roots[0].legal,roots[1].legal),'paired root state');result.pairs.push({pair:p,Xi:games.reduce((a,x)=>a+x.score,0)/2,same_side_winner:games[0].winner===games[1].winner,layer:games[0].layer});}
result.WDL=[result.games.filter(x=>x.score===1).length,result.games.filter(x=>x.score===.5).length,result.games.filter(x=>x.score===0).length];result.mean=result.pairs.reduce((a,x)=>a+x.Xi,0)/8;result.eps=Math.sqrt(Math.log(40)/16);result.identification=[result.mean,result.mean];
fs.writeFileSync(D+'replay-result.json',JSON.stringify(result,null,2));console.log(JSON.stringify({games:result.games,rows:result.rows,WDL:result.WDL,pairs:result.pairs,mean:result.mean,counts:result.counts}));
