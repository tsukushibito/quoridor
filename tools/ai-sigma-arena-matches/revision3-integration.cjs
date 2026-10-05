const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{diagnosticRealBackend}=require('./match-entry.cjs');const ROOT=path.resolve(__dirname,'../..'),OUT=ROOT+'/.artifacts/ai-sigma/runs/SIGMA-PAIRED-MATCHES/revision3';const golden=JSON.parse(fs.readFileSync(ROOT+'/.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json')).fixtures.find(f=>f.id==='initial-p1');const f={id:golden.id,legal_prefix:golden.legal_prefix},rows=[],stops=[];let b;
const save=()=>fs.writeFileSync(OUT+'/integration.json',JSON.stringify({rows,stops,holdout_engine_sends:0,real_games:0,NN_repetitions:1},null,2));
(async()=>{try{
 b=await diagnosticRealBackend({out:OUT+'/session1'});
 for(const engine of ['native','candidate','reference']){const result=await b.submit(engine,f,500,91,4096);rows.push({session:1,engine,result});save();}
 const timeout=await b.submit('native',{...f,diagnostic_step_delay_ms:500},10,0,4096);rows.push({session:1,engine:'native',phase:'watchdog',result:timeout});save();assert.equal(timeout.accepted,false);assert.equal(timeout.error,'NO_RESPONSE_TIMEOUT');assert.equal(timeout.action,undefined);
 stops.push({session:1,proof:await b.stop()});b=null;save();
 b=await diagnosticRealBackend({out:OUT+'/session2'});
 for(const engine of ['native','candidate','reference']){const result=await b.submit(engine,f,500,91,4096);rows.push({session:2,engine,result});save();}
 }finally{if(b){stops.push({session:2,proof:await b.stop()});b=null;}save();}
 const positives=rows.filter(r=>r.phase!=='watchdog');const summary={positive_requests:positives.length,accepted:positives.filter(r=>r.result.accepted).length,all_fresh_positive:positives.filter(r=>r.session===2).length===3&&positives.filter(r=>r.session===2).every(r=>r.result.accepted),all_positive:positives.length===6&&positives.every(r=>r.result.accepted),stop_PID0:stops.every(s=>s.proof.remaining_pids===0),no_tail_guarantee:true,holdout_engine_sends:0,games:0};fs.writeFileSync(OUT+'/integration-summary.json',JSON.stringify(summary,null,2));console.log(JSON.stringify(summary));if(!summary.all_positive)process.exitCode=1;
})().catch(e=>{save();fs.writeFileSync(OUT+'/integration-failure.json',JSON.stringify({error:e.message,stack:e.stack},null,2));console.error(e);process.exitCode=1});
