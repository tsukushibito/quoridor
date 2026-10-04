from pathlib import Path
import json,hashlib,datetime
R=Path.cwd();T=R/'tools/ai-sigma-teacher-throughput';D=R/'research-data/ai-sigma/frame16-teacher-throughput';A=T/'architecture-control';O=D/'architecture-control'
s=(T/'runner.py').read_text().replace("c=json.loads", "A=T/'architecture-control';O=D/'architecture-control'\nc=json.loads",1)
s=s.replace('2026-10-04T09:25:50Z','2026-10-04T09:15:50Z').replace('2026-10-04T09:35:50Z','2026-10-04T09:25:50Z')
s=s.replace("reg=json.loads((D/'preregister.json').read_text());binding=json.loads((D/'source-freeze.json').read_text())","reg=json.loads((D/'preregister.json').read_text());binding=json.loads((O/'source-freeze.json').read_text())")
start=s.index("prior=[json.loads(p.read_text())");end=s.index("save('admission.json'",start)
s=s[:start]+'''prior=[json.loads(p.read_text())for p in(D/'jobs').glob('*/process.json')];newprior=[json.loads(p.read_text())for p in(O/'jobs').glob('*/process.json')]
spent=355.917963652+sum(p['jobwall_seconds']for p in newprior);samples=243888+sum((p.get('sample_equivalent')or 0)for p in newprior);unknown=[p for p in newprior if p.get('sample_equivalent')is None]
assert not unknown,'PRIOR_NEW_SAMPLE_UNKNOWN';assert spent+c['job_seconds']<=1800 and sum(p['jobwall_seconds']for p in newprior)+c['job_seconds']<=650
assert samples+c['NN_cap']<=900000 and sum(p['sample_equivalent']for p in newprior)+c['NN_cap']<=505000
if c['kind']=='generation':
 assert c['max_batch']==8 and c['active_per_worker']==8 and c['NN_cap']<=250000
 assert json.loads((O/'parity-pass.json').read_text())['primary']is None,'GRAPH_PARITY_REQUIRED'
 assert sum(p['kind']=='generation'for p in newprior)<2
else:assert c['NN_cap']<=5000
storage=json.loads((D/'storage-admission.json').read_text());assert storage['unused_after_reservation_B']>=0
# Existing actual and immutable old Git are retained; only bounded additional outputs are forecast.
gitupper=11214512+sum(p.stat().st_size for root in [A,O]for p in root.rglob('*')if p.is_file() and not '/jobs/'in str(p))
forecast=usage()+gitupper+4*1024**2+(20*1024**2 if c['kind']=='generation'else 1*1024**2)
assert forecast<112*1024**2,('STORAGE_CURRENT_GIT_FORECAST',forecast)
''' +s[end:]
s=s.replace("uniqueGit_remaining_forecast_B=usage()+32*1024**2","uniqueGit_remaining_forecast_B=gitupper,all_inclusive_forecast_B=forecast")
s=s.replace("str(T/c['script'])","str(A/c['script'])")
s=s.replace("if usage()+16*1024**2>=112*1024**2","if usage()+gitupper+4*1024**2>=112*1024**2")
s=s.replace("tracked={};reason=None;peak=0;gpupeak=0;startUTC=utc();limit", "tracked={};reason=None;peak=0;gpupeak=0;startUTC=utc();save('actual-start.json',dict(UTC=startUTC,command=cmd,source_git=c['source_git'],runner_pid=os.getpid(),runner_tick=table()[os.getpid()]['tick']));limit")
(A/'runner.py').write_text(s)
parity="""'use strict';const fs=require('fs'),assert=require('assert'),{performance}=require('perf_hooks'),{Pipe}=require('../pipe.cjs');const ROOT=process.cwd(),out=process.argv[2],games=JSON.parse(fs.readFileSync(ROOT+'/research-data/ai-sigma/frame16-teacher-throughput/openings.json')).games;const save=(n,x)=>fs.writeFileSync(out+'/'+n,JSON.stringify(x,null,2)+'\\n');
(async()=>{const start=performance.now(),p=new Pipe('/home/vscode/.cache/inference/envs/quoridor-training/bin/python',['-u',__dirname+'/provider.py','--sample-cap','324','--max-batch','8'],{timeoutMs:50000}),checks=[];let info,stop,primary=null;try{info=await p.ask({op:'info',request_id:'init'});assert(info.ok,JSON.stringify(info));assert.equal(info.result.graph_startup_samples,108);let seq=0;for(let B=1;B<=8;B++)for(let fixture=0;fixture<2;fixture++){const items=Array.from({length:B},(_,i)=>({id:'fixed-'+B+'-'+fixture+'-'+i,features_bits648:games[(i*3+1+fixture*17)%48].opening.root_state.features_bits})),all={};for(const backend of ['cpuort','eager','cuda']){all[backend]=await p.ask({op:'infer_batch',request_id:'p'+(++seq),backend,items});assert(all[backend].ok,JSON.stringify(all[backend]));}let diff=0,ratio=0,graphEager=0;for(let i=0;i<B;i++){for(const k of Object.keys(all))assert.equal(all[k].result.items[i].id,items[i].id);const a=[...all.cpuort.result.items[i].logits,all.cpuort.result.items[i].value],b=[...all.cuda.result.items[i].logits,all.cuda.result.items[i].value],e=[...all.eager.result.items[i].logits,all.eager.result.items[i].value];for(let j=0;j<137;j++){assert(Number.isFinite(b[j]));diff=Math.max(diff,Math.abs(a[j]-b[j]));ratio=Math.max(ratio,Math.abs(a[j]-b[j])/(1e-4+1e-4*Math.abs(a[j])));graphEager=Math.max(graphEager,Math.abs(e[j]-b[j]));}}assert(ratio<=1,'CPU_GRAPH_TOL');checks.push({B,fixture,max_absdiff:diff,max_tol_ratio:ratio,graph_eager_maxabs:graphEager,IDs_pass:true,f32_finite_pass:true,CPU_samples:B,eager_samples:B,replay_samples:B,eager_cost:all.eager.result.batchcost,replay_cost:all.cuda.result.batchcost});save('checks-so-far.json',checks);}}catch(e){primary={error:e.stack,provider_stderr:p.stderr};}finally{try{stop=await p.ask({op:'stop',request_id:'stop'})}catch(e){stop={error:e.stack,provider_stderr:p.stderr}}const exit=await p.close();save('result.json',{info,checks,stop,exit,primary,elapsed_s:(performance.now()-start)/1000,NN_samples:stop?.result?.single_sample_equivalent??null,tol:'abs1e-4+rtol1e-4',fulltree_or_teacher_quality_proved:false});console.log(JSON.stringify({checks:checks.length,primary,exit}));if(primary)process.exitCode=1;}})().catch(e=>{console.error(e.stack);process.exitCode=1});"""
(A/'parity.cjs').write_text(parity)
for name,kind,script,cap,seconds in [('parity-r1','parity','parity.cjs',324,50),('graph-r1','generation','generate.cjs',250000,300),('graph-confirmation','generation','generate.cjs',250000,300)]:
 c=json.loads((D/'baseline-config.json').read_text());c.update(run_id='throughput221-phase2-'+name,kind=kind,script=script,NN_cap=cap,job_seconds=seconds,job_out=str(O/'jobs'/name),science_deadline='2026-10-04T09:25:50Z',source_git='PENDING_FREEZE');(O/(name+'-config.json')).write_text(json.dumps(c,indent=2)+'\n')
# Bind private phase2 source and unchanged generation boundaries; source-freeze is written once before first science.
files=list(A.glob('*'))+[T/f for f in ['worker.cjs','broker.cjs','pipe.cjs','adapter.py','qualify.cjs']]+[D/'openings.json',O/'preregister.json',R/'tools/ai-sigma-manygame-generation/pause-monitor.cjs']
b={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files if p.is_file()},'old_source_immutable':True}
(O/'source-freeze.json').write_text(json.dumps(b,indent=2)+'\n')
