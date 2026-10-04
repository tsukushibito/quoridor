"""225 bounded owned-process guardian; coldinit, cleanup, all attempts included."""
from pathlib import Path
import ctypes,datetime,hashlib,json,os,signal,subprocess,sys,time
R=Path.cwd();T=R/'tools/ai-sigma-worker-balance';D=R/'research-data/ai-sigma/frame18-worker-balance'
A=T;O=D
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['job_out']);assert not out.exists(),'ATTEMPT_ALREADY_EXISTS';out.mkdir(parents=True)
st=time.monotonic();utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();end=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp();save=lambda n,v:(out/n).write_text(json.dumps(v,indent=2)+'\n')
os.sched_setaffinity(0,{0});ctypes.CDLL(None).prctl(36,1,0,0,0)
def table():
 tab={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   s=(p/'stat').read_text().rsplit(')',1)[1].split();tab[int(p.name)]=dict(pid=int(p.name),ppid=int(s[1]),tick=int(s[19]),state=s[0],RSS=int(s[21])*4096)
  except (OSError,ValueError):pass
 return tab

def usage():return sum(p.stat().st_size for root in [T,D]for p in root.rglob('*')if p.is_file())
assert time.time()<end('2026-10-04T11:15:18Z'),'NEWHEAVY_DEADLINE'
reg=json.loads((D/'preregister.json').read_text());binding=json.loads((O/'source-freeze.json').read_text())
for p,h in {**reg['readonly'],**binding['files']}.items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,('SOURCE_CHANGED',p)
controls=[]
for issue in ['quoridor-4lc','quoridor-4lc.225']:
 z=subprocess.run(['bash','scripts/dev/beads.sh','show',issue,'--json'],capture_output=True,text=True,timeout=10,check=True);q=json.loads(z.stdout)[0];assert q['status']=='in_progress' and 'paused-by-user' not in q.get('labels',[]),'OWNER_OR_PAUSE'
 if issue.endswith('.225'):assert q['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746'
 controls.append({k:q.get(k)for k in ['id','status','assignee','labels']})
schpath=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');sch=json.loads(schpath.read_text());assert sch['phase']=='running' and not sch.get('recovery_required');quiet=sch['next_at']-time.time()if sch.get('next_at')else None
if sch['owned']is None:assert quiet is not None and quiet>=c['job_seconds']+30,'SUPERVISOR_QUIET_SHORT'
# User withdrew LLM turn-time cap. An owned LLM turn alone is not a physical CPU job gate.
# Existing actual script/process admission below must still show no foreign science/critic compute.
if sch['owned']is not None:assert c.get('allow_owned_LLM_with_physical_guard')is True,'CURRENT_OWNED_PHYSICAL_POLICY_REQUIRED'
assert c.get('runtime_loaded'),'NEW_RUNTIME_BINDING_REQUIRED'
loadedpath=Path(c['runtime_loaded']);loaded=json.loads(loadedpath.read_text());assert loaded['max_turn_seconds'] is None and loaded['period_seconds']==1200
for ip in ['.artifacts/research-team/scheduler-sigma-continuation-20261001/config.json','.artifacts/research-team/scheduler-sigma-continuation-20261001/contract.json']:
 pass
assert loaded['parent_sha']==hashlib.sha256((R/'docs/design/ai-sigma-continuation-20261001.md').read_bytes()).hexdigest(),'CURRENT_PARENT_BINDING'
monitor=Path(c.get('runtime_monitor')or str(Path(loaded['run'])/'monitor-observation.json'));mon=json.loads(monitor.read_text());assert time.time()-monitor.stat().st_mtime<120,'CURRENT_MONITOR_STALE'
for role in ['scheduler','monitor']:
 z=loaded[role].get('process',loaded[role]);actual=table().get(z['pid']);assert actual and str(actual['tick'])==str(z['start_ticks']),'RUNTIME_CURRENT_IDENTITY'
current=[];foreign=[];rss=0
for pid,z in table().items():
 if pid==os.getpid() or z['state']=='Z':continue
 try:args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0');aff=sorted(os.sched_getaffinity(pid))
 except (OSError,UnicodeError):continue
 script=next((a for a in args[1:5]if a.endswith(('.py','.cjs','.js','.sh'))),'');arg=' '.join(args)
 if 'tools/ai-sigma-'in script or 'tools/nnue-training/'in script or 'research-data/ai-sigma/'in script or 'tools/research-team/'in script or 'faithful-native'in args[0] or '.artifacts/ai-sigma/continuation-20261001/'in script:
  rss+=z['RSS'];current.append({**z,'affinity':aff,'script':script,'argv':arg[:250]})
  if ('tools/ai-sigma-'in script or 'tools/nnue-training/'in script or 'research-data/ai-sigma/'in script or 'faithful-native'in args[0]) and not script.endswith(('/save_git.py','/save.py','/pack.py')):foreign.append(current[-1])
assert not foreign,('CURRENT_FOREIGN_SCIENCE_OR_CRITIC',foreign)
gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,timeout=5,check=True).stdout.strip();assert not gpu,('CURRENT_GPU',gpu)
assert rss+6*1024**3<8*1024**3,'PARENT_RSS';assert int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024>6*1024**3
newprior=[json.loads(p.read_text())for p in(O/'jobs').glob('*/process.json')]
spent=sum(p['jobwall_seconds']for p in newprior);samples=sum((p.get('sample_equivalent')or 0)for p in newprior);unknown=[p for p in newprior if p.get('sample_equivalent')is None]
assert not unknown,'PRIOR_NEW_SAMPLE_UNKNOWN'
assert len(newprior)<3 and spent+c['job_seconds']<=1500 and samples+c['NN_cap']<=1050000
assert c['max_batch']==8 and c['active_per_worker']==8 and c['NN_cap']<=350000 and c['job_seconds']<=420
assert hashlib.sha256((R/'tools/ai-sigma-teacher-throughput/codec-control/provider.py').read_bytes()).hexdigest()=='a422650a8cf01b61870c28e800b4595db7e4699166a5b02518ac23e0cdc8666e','UNCHANGED_PROVIDER_PARITY_REUSE'
storage=json.loads((O/'storage-admission.json').read_text());assert storage['unused_after_reservation_B']>=0
stageusage=lambda:sum(p.stat().st_size for root in[A,O]for p in root.rglob('*')if p.is_file())
gitupper=sum(p.stat().st_size for root in[A,O]for p in root.rglob('*')if p.is_file()and'/jobs/'not in str(p))
forecast=stageusage()+gitupper+4*1024**2+80*1024**2
assert forecast<224*1024**2,('NEW_STORAGE_FORECAST',forecast)
oldcurrent=sum(p.stat().st_size for root in[R/'tools/ai-sigma-teacher-throughput',R/'research-data/ai-sigma/frame16-teacher-throughput']for p in root.rglob('*')if p.is_file())
assert oldcurrent<=storage['old_scopes_actual_upper_B'],'OLD_SCOPE_FORECAST_UNKNOWN'
save('admission.json',dict(UTC=utc(),controls=controls,current=current,foreign=foreign,quiet_seconds=quiet,scheduler=sch,monitor_path=str(monitor),monitor_observation=mon,parent_current_RSS=rss,job_RAM=6*1024**3,RAM_guard=int(5.5*1024**3),GPU_current=[],CPU_cores=[0,2,4,6],logical_CPU_max=4,prior_jobwall_s=spent,prior_samples=samples,storage_current_B=stageusage(),old_scope_actual_B=oldcurrent,new_runtime_loaded_path=str(loadedpath),uniqueGit_remaining_forecast_B=gitupper,all_inclusive_forecast_B=forecast,storage_ledger=storage,physical_current_point_not_allhost_guarantee=True))
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',SIGMA_SOURCE=c['source_git']);cmd=['/home/vscode/.local/bin/node','--max-old-space-size=192',str(A/c['script']),str(out)if c['kind']=='parity'else str(Path(sys.argv[1]).resolve())]
tracked={};reason=None;peak=0;gpupeak=0;startUTC=utc();save('actual-start.json',dict(UTC=startUTC,command=cmd,source_git=c['source_git'],runner_pid=os.getpid(),runner_tick=table()[os.getpid()]['tick']));limit=min(time.time()+c['job_seconds'],end('2026-10-04T11:25:18Z'))
with(out/'stdout.txt').open('w')as log:
 child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);tracked[(child.pid,table()[child.pid]['tick'])]=table()[child.pid]
 def group():
  tab=table();active={p for p,t in tracked if tab.get(p,{}).get('tick')==t};active|={p for p,z in tab.items()if z['ppid']==os.getpid()};change=True
  while change:
   new={p for p,z in tab.items()if z['ppid']in active};change=not new<=active;active|=new
  for p in active:
   if p in tab:tracked[(p,tab[p]['tick'])]=tab[p]
  return [tab[p]for p in active if p in tab]
 def kill(sig):
  for z in group():
   if z['state']!='Z':
    try:
     if table().get(z['pid'],{}).get('tick')==z['tick']:os.kill(z['pid'],sig)
    except ProcessLookupError:pass
 while child.poll()is None:
  members=group();family=sum(z['RSS']for z in members)+table()[os.getpid()]['RSS'];peak=max(peak,family)
  if family>=5.5*1024**3:reason='RAM_GUARD'
  if stageusage()+gitupper+4*1024**2>=224*1024**2:reason='STORAGE_GUARD'
  # If an actual foreign scientific script starts during the job, stop this owned job, never interrupt theirs.
  for fp,fz in table().items():
   if fp==os.getpid()or fz['state']=='Z'or(fp,fz['tick'])in tracked:continue
   # Descendants may spawn between group() and this snapshot; current ancestry still proves owned.
   ancestry=table();parent=fz['ppid'];seen=set();owned=False
   while parent in ancestry and parent not in seen:
    if parent==os.getpid()or(parent,ancestry[parent]['tick'])in tracked:owned=True;break
    seen.add(parent);parent=ancestry[parent]['ppid']
   if owned:continue
   try:fa=Path(f'/proc/{fp}/cmdline').read_bytes().decode().split('\0')
   except(OSError,UnicodeError):continue
   fs=next((a for a in fa[1:5]if a.endswith(('.py','.cjs','.js','.sh'))),'')
   if ('tools/ai-sigma-'in fs or 'tools/nnue-training/'in fs or 'research-data/ai-sigma/'in fs or (fa and 'faithful-native'in fa[0]))and not fs.endswith(('/save_git.py','/save.py','/pack.py')):
    save('foreign-compute-detected.json',dict(UTC=utc(),pid=fp,tick=fz['tick'],ppid=fz['ppid'],script=fs,argv=fa[:6],ancestry_seen=sorted(seen)));reason='CURRENT_FOREIGN_COMPUTE_STARTED'
  for z in members:
   try:
    for tid in Path(f'/proc/{z["pid"]}/task').iterdir():
     aff=sorted(os.sched_getaffinity(int(tid.name)))
     if len(aff)!=1 or aff[0]not in[0,2,4,6]:reason='AFFINITY_UNKNOWN'
   except (OSError,ProcessLookupError):pass
  if time.time()>=limit:reason='JOB_OR_SCIENCE_DEADLINE'
  if (out/'PAUSE').exists():reason='PAUSED'
  if reason:break
  time.sleep(.1)
 if reason:kill(signal.SIGTERM)
 try:code=child.wait(timeout=2)
 except subprocess.TimeoutExpired:kill(signal.SIGKILL);code=child.wait(timeout=2)
 for z in group():
  if z['state']!='Z':
   try:os.kill(z['pid'],signal.SIGKILL)
   except ProcessLookupError:pass
 for _ in range(200):
  try:
   pid,status=os.waitpid(-1,os.WNOHANG)
   if pid==0:time.sleep(.005)
  except ChildProcessError:break
res=json.loads((out/'result.json').read_text())if(out/'result.json').exists()else{};sample=res.get('NN_samples')if c['kind']=='parity'else res.get('providerStop',{}).get('single_sample_equivalent');remaining=group()
receipt=dict(issue=c['issue'],run=c['run_id'],kind=c['kind'],max_batch=c.get('max_batch'),startUTC=startUTC,endUTC=utc(),jobwall_seconds=time.monotonic()-st,exit=code,stop_reason=reason,runner_pid=os.getpid(),runner_tick=table()[os.getpid()]['tick'],tracked=list(tracked.values()),remaining=remaining,peak_aggregate_RSS=peak,command=cmd,source_git=c['source_git'],sample_equivalent=sample,NN_cap=c['NN_cap'],current_exact_absent=not remaining,all_child_waited=not remaining,instant_peak_not_guaranteed=True)
save('process.json',receipt);print(json.dumps({k:v for k,v in receipt.items()if k not in['tracked','command']}));sys.exit(0 if code==0 and not reason and not remaining else 1)
