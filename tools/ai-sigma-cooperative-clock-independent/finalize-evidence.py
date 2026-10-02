import pathlib,json,hashlib,datetime,subprocess,os
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-CLOCK-INDEPENDENT';D=R/'research-data/ai-sigma/100-cooperative-clock-independent';D.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
input_before=read(O/'input-binding-before.json');after={'source':{},'direct':{},'archive':{},'mismatches':[]}
for k,v in input_before['source'].items():
 h=sha(R/k);after['source'][k]=h
 if h!=v:after['mismatches'].append(k)
print('input-before-keys',list(input_before))
for k,want in input_before['direct'].items():
 p=pathlib.Path(k);after['direct'][k]=sha(p)
 if sha(p)!=want:after['mismatches'].append(k)
for p in (R/'research-data/ai-sigma/97-tail-transport').iterdir():
 if p.is_file() and p.suffix=='.json':after['direct'][str(p.relative_to(R))]=sha(p)
after['archive']=sha(R/'research-data/ai-sigma/97-tail-transport/runs-and-evidence.tar.gz');assert after['archive']==input_before['archive_sha'];(O/'input-after.json').write_text(json.dumps(after,indent=2)+'\n');assert not after['mismatches']
# Compare necessary shared dependencies to immutable source Git. This is post-run capture,
# not a fabricated before-first-read ledger.
base=R/'tools/ai-sigma-actual-boundary-repair';deps={}
for n in ['caller.cjs','judge.cjs','early-cache.cjs','backend-envelope.cjs','cleanup.cjs','final-envelope.cjs','reference-core.js','reference-control-run.js','host.js','game.js','context.js','kernel_boundary.py','owned_ledger.py']:
 p=base/n
 if not p.exists():continue
 b=subprocess.check_output(['git','show','83bb0ce4ea55b210f1657913ab2d6f2fa728eac5:'+str(p.relative_to(R))]);assert b==p.read_bytes();deps[str(p.relative_to(R))]={'SHA':sha(p),'same_git83':True,'capture':'post-run Git bytes comparison'}
for name,want in [('models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx','d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'),('.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm','1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'),('.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json','060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a')]:
 p=R/name;assert sha(p)==want;deps[name]={'SHA':want,'bytes':p.stat().st_size,'capture':'post-run fixed input verification; model ready runtime also checked digest'}
(O/'necessary-dependencies-fixed-Git.json').write_text(json.dumps(deps,indent=2)+'\n')
processes=[read(p) for p in O.glob('*.process.json')];ids=set()
def walk(x):
 if isinstance(x,dict):
  p=x.get('pid',x.get('PID'));t=x.get('starttick',x.get('start_ticks'))
  if p and t:ids.add((int(p),int(t)))
  for k in ['runner','child']:
   if x.get(k+'_pid') and x.get(k+'_starttick'):ids.add((int(x[k+'_pid']),int(x[k+'_starttick'])))
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
for x in processes:walk(x)
run=O/'critic100-primary-r1';session=run/'real-critic100-primary-r1-session1';drop=read(session/'model-drop.json');control=read(session/'controlled-stop.json');monitor=read(run/'pause-monitor-stop.json');walk(control);walk(monitor)
live=[]
for pid,t in ids:
 try:
  s=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
  if int(s[19])==t:live.append([pid,t,s[0]])
 except OSError:pass
assert not live;assert all(not p['remaining'] and not p['unknown_adopted'] for p in processes);assert drop['handles']==drop['activeNN']==0 and control['controlledPID0'];assert monitor['all_owned_read_callbacks_waited'] and not monitor['pending_children'] and not monitor['active_monitor_timer']
clock=[]
for origin in [O/'upstream-needed/clock-factor-primary-r1/real-clock-factor-primary-r1-session1/browser',session/'browser']:
 start=read(origin/'clock-start.json');end=read(origin/'clock-end.json');row={'source':str(origin.relative_to(R))}
 for k in ['page','worker']:
  a,b=start[k],end[k];assert len(a['samples'])==len(b['samples'])==12
  for c in [a,b]:
   lo=max(v['remote']-v['end']-.1 for v in c['samples']);hi=min(v['remote']-v['start']+.1 for v in c['samples']);assert abs(lo-c['lo_ms'])<1e-6 and abs(hi-c['hi_ms'])<1e-6 and lo<=hi
  assert max(a['lo_ms'],b['lo_ms'])<=min(a['hi_ms'],b['hi_ms']);row[k]={'start_lo':a['lo_ms'],'start_hi':a['hi_ms'],'end_lo':b['lo_ms'],'end_hi':b['hi_ms'],'intersections_overlap':True,'pings_each':12}
 clock.append(row)
(O/'clock-independent.json').write_text(json.dumps(clock,indent=2)+'\n')
summary={'issue':'quoridor-4lc.100','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'NN_end':next(p['end'] for p in processes if p['name']=='nn-primary-r1'),'identity_count':len(ids),'same_identity_live':live,'drop':drop,'controlled':{'forced':control['forced'],'controlledPID0':control['controlledPID0'],'remaining_pids':control['cleanup']['remaining_pids'],'waited':control['cleanup']['waited']},'monitor':{k:monitor[k] for k in ['state','failure','pending_children','all_owned_read_callbacks_waited','active_monitor_timer']},'original_source_hashafter_match':True,'all_jobs':[{'name':p['name'],'start':p['start'],'end':p['end'],'exit':p['exit'],'reason':p['stop_reason'],'remaining':p['remaining'],'peakRSS':p['peak_group_plus_runner_RSS'],'peakStorage':p['peak_allocated_bytes'],'CPU':p['assigned_CPU'],'observed_TIDs_match':p['all_observed_TIDs_at_assigned_CPU']} for p in processes],'runtime_source_stopped_before_report':True,'instant_peak_background_allCPU_not_guaranteed':True,'combined_scope_guarantee':'conservative observed holdings only; no whole host inventory','actual_go':False,'source_runtime_git':'997e27496ec5cec1845dbd92ab164504d7492b06','config_Git_field':'83bb0ce4ea55b210f1657913ab2d6f2fa728eac5 is immutable upstream producer; adapter source identified separately, not same Git commit'}
(O/'source-runtime-stop-final.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'identities':len(ids),'current0':not live,'NN_end':summary['NN_end'],'jobs':len(processes),'peakRSS':max(p['peak_group_plus_runner_RSS'] for p in processes),'allocatedPeak':max(p['peak_allocated_bytes'] for p in processes)}))
