'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert'),zlib=require('zlib');
const {r}=require('../ai-sigma-native-baseline/reference.cjs').createReference();
const {target,validate}=require('../ai-sigma-manygame-generation/schema.cjs');
const ROOT=path.resolve(__dirname,'../..'),D=ROOT+'/research-data/ai-sigma/frame14-l2-test',A=ROOT+'/.artifacts/ai-sigma/frame14-l2-test';
const manifest=JSON.parse(fs.readFileSync(D+'/openings.json')),specs=manifest.games,records=[],statuses=[],summaries=[];
const read=p=>fs.existsSync(p)?JSON.parse(fs.readFileSync(p)):null,lines=p=>fs.existsSync(p)?fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
const sha=v=>crypto.createHash('sha256').update(typeof v==='string'?v:JSON.stringify(v)).digest('hex');
const save=(n,v)=>fs.writeFileSync(D+'/'+n,JSON.stringify(v,null,2)+'\n');
const gz=(n,rows)=>{const b=zlib.gzipSync(rows.map(r=>JSON.stringify(r)).join('\n')+'\n');fs.writeFileSync(D+'/'+n,b);return{path:D+'/'+n,SHA256:sha(b),rows:rows.length};};
const canonical=x=>[...x].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
// QF1 canonical signature is owned by195 and applied by its stopped/hash-bound adapter.

for(const job of manifest.jobs){
 const out=A+(job==='test'?'/test-sealed':'')+'/native198-'+job+'-r1',proc=read(out+'/process.json'),result=read(out+'/result.json'),raw=[],finals=[],starts=[];
 if(proc)assert.equal(proc.remaining.length,0,'CHILD_REMAINS');
 for(const core of [2,4,6]){raw.push(...lines(out+'/core'+core+'/raw-rows.jsonl'));finals.push(...lines(out+'/core'+core+'/games.jsonl'));starts.push(...lines(out+'/core'+core+'/starts.jsonl'));}
 if(starts.length&&!proc)throw Error('LIVE_EXPORT_REFUSED_UNREAPED_WRITER');
 const gameStatuses=[];
 for(const spec of specs.filter(s=>s.job===job)){
  const game=finals.find(g=>g.game_id===spec.game_id)??{game_id:spec.game_id,family:spec.family,split:spec.split,status:starts.some(s=>s.game_id===spec.game_id)?'REGISTERED_UNFINISHED_UNKNOWN':'NOT_STARTED',winner:null,reason:proc?'RUN_FAILED_OR_SLOT_NOT_REACHED':'JOB_NOT_ADMITTED',rows:raw.filter(r=>r.game_id===spec.game_id).length};
  gameStatuses.push({...game,train_slot:spec.split==='train'?spec.partition_slot:null,opening_ply:spec.target_ply});
  if(!spec.generated)continue;
  let state=r.fromPrefix(spec.opening.legal_prefix);
  for(const row of raw.filter(r=>r.game_id===spec.game_id).sort((a,b)=>a.ply-b.ply)){
   assert.equal(row.family,spec.family);assert.equal(row.split,spec.split==='test'?'evaluation':spec.split);assert.equal(row.state_key,state._positionKey());assert.equal(row.side,state.getCurrentPlayer());assert.equal(row.ply,state.depth);
   assert.equal(JSON.stringify(row.features648_bits),JSON.stringify(r.portState(state).features_bits));assert.equal(JSON.stringify(row.legal_order209),JSON.stringify(r.portState(state).legal));assert.equal(JSON.stringify(canonical(row.history_counts)),JSON.stringify(canonical(state.position_history)));
   target(row,game.winner??null);validate(row,64);row.split=spec.split;row.policy_eligible=true;row.joint_eligible=row.value_eligible;row.legal_mask136=Array(136).fill(0);for(const [a,k]of row.mapping136)row.legal_mask136[k]=1;
   const historyKey=sha(['RuleA-state-history-v1',row.state_key,row.side,canonical(row.history_counts)]),full=sha([row.state_key,row.side,row.ply,canonical(row.history_counts)]);
   const info={id:row.row_id,game_id:row.game_id,group:spec.family,family:spec.family,split:spec.split,train_slot:spec.split==='train'?spec.partition_slot:null,cohort:'opening-'+spec.target_ply,opening_ply:spec.target_ply,state_key:row.state_key,history_key:historyKey,full_state_key:full,side:row.side,features648SHA:sha(row.features648_bits),policy_eligible:true};
   records.push({row,info});
   const action=state.getLegalActions().find(a=>r.rustAction(state,a)===row.action209);assert(action,'ACTION_REPLAY');state=state.next(action);
  }
  if(['GOAL','DRAW200','DRAW_NOLEGAL'].includes(game.status)){const term=r.terminalResult(state);assert(term&&term.winner===game.winner,'TERMINAL_REPLAY');}
 }
 statuses.push(...gameStatuses);
 const rs=records.filter(x=>specs.find(g=>g.game_id===x.info.game_id).job===job),broker=read(out+'/broker.json');
 const Rpolicy=rs.length,Rz=rs.filter(x=>x.row.value_eligible).length,Rjoint=rs.filter(x=>x.row.joint_eligible).length;
 summaries.push({job,planned_games:24,status_counts:Object.fromEntries([...new Set(gameStatuses.map(g=>g.status))].map(k=>[k,gameStatuses.filter(g=>g.status===k).length])),Rpolicy,Rz,Rjoint,allattempt_jobwall_s:proc?.jobwall_seconds??null,rates:proc?{Rpolicy:Rpolicy/proc.jobwall_seconds,Rz:Rz/proc.jobwall_seconds,Rjoint:Rjoint/proc.jobwall_seconds}:null,logical_worker_requests:result?.NN??null,physical_provider_samples:result?.providerStop?.single_sample_equivalent??null,providerStop:result?.providerStop??null,batch:broker?.stats??null,providerCost:broker?.providerCost??null,sampled_peak_RSS:proc?.peak_aggregate_RSS??null,all24_status_and_plies:gameStatuses.map(g=>({game_id:g.game_id,status:g.status,total_ply:g.plies??null,rows:g.rows??0})),attempt:proc?{exit:proc.exit,stop_reason:proc.stop_reason}:null});
}
assert.equal(new Set(specs.map(x=>x.family)).size,24,'FAMILY_CROSS_SPLIT');assert.equal(new Set(records.map(x=>x.info.id)).size,records.length,'DUPLICATE_ROW_ID');
const outputs={};
for(const split of ['test']){
 const list=records.filter(x=>x.info.split===split),base=split==='test'?'test-sealed/':'';
 outputs[split]={teacher:gz(base+split+'-teacher-rows.jsonl.gz',list.map(x=>x.row)),state_journal:gz(base+split+'-state-journal.jsonl.gz',list.map(x=>x.info))};
}
save('test-sealed/all24-full-status.json',statuses);save('all24-slot-status.json',statuses.map(({game_id,family,split,status,reason,rows,plies,opening_ply})=>({game_id,family,split:split==='evaluation'?'test':split,status,reason,rows,plies,opening_ply}))); save('generation-summary.json',{issue:'quoridor-4lc.198',jobs:summaries,Rpolicy:records.length,Rz:records.filter(x=>x.row.value_eligible).length,Rjoint:records.filter(x=>x.row.joint_eligible).length,allattempt_jobwall_s:summaries.reduce((s,x)=>s+(x.allattempt_jobwall_s??0),0),planned24:24,outputs,shared_QF1_exposure_adapter_pending:true,teacher_truth_or_NI:false});
console.log(JSON.stringify({rows:records.length,jobs:summaries.map(x=>({job:x.job,status:x.status_counts,Rjoint:x.Rjoint,wall:x.allattempt_jobwall_s}))}));
