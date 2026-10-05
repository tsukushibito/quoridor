"""Bounded private job guardian: identity-owned descendants, admission and sampled resources."""
import ctypes,datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];T=Path(__file__).resolve().parent;D=ROOT/'research-data/ai-sigma/frame14-distance-test';A=ROOT/'.artifacts/ai-sigma/frame14-distance-test';A.mkdir(parents=True,exist_ok=True)
c=json.loads(Path(sys.argv[1]).read_text());name=c['run_id'];assert name.startswith('native201-') and '/' not in name
out=Path(c['job_out']);assert not out.exists(),'ATTEMPT_ALREADY_EXISTS';out.mkdir(parents=True)
wall=time.monotonic();utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();end=lambda s:datetime.datetime.fromisoformat(s).timestamp()
assert time.time()<end('2026-10-04T02:00:00+00:00'),'NEWHEAVY_CUTOFF'
prior=0.0+sum(json.loads(p.read_text())['jobwall_seconds']for p in A.rglob('process.json'));assert prior+c['job_seconds']<=360,'TOTAL_BUDGET_ADMISSION'
os.sched_setaffinity(0,{c['management_core']});assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
save=lambda n,v:(out/n).write_text(json.dumps(v,indent=2)+'\n')
def table():
 r={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   s=(p/'stat').read_text().rsplit(')',1)[1].split();r[int(p.name)]={'pid':int(p.name),'ppid':int(s[1]),'tick':int(s[19]),'state':s[0],'RSS':int(s[21])*4096}
  except (OSError,ValueError):pass
 return r

def allocated(bases):
 seen=set();n=0
 for base in bases:
  if not base.exists():continue
  for p in base.rglob('*'):
   try:
    if not p.is_file():continue
    x=p.stat();k=(x.st_dev,x.st_ino)
    if k not in seen:seen.add(k);n+=x.st_blocks*512
   except FileNotFoundError:pass
 return n
controls=[]
for issue in ['quoridor-4lc','quoridor-4lc.201']:
 z=subprocess.run(['bash',str(ROOT/'scripts/dev/beads.sh'),'show',issue,'--json'],capture_output=True,text=True,timeout=10,check=True);x=json.loads(z.stdout)[0];assert x['status']=='in_progress' and 'paused-by-user' not in x.get('labels',[]),'CONTROL_UNKNOWN_OR_PAUSE'
 if issue.endswith('.201'):assert x['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746','OWNER'
 controls.append({k:x.get(k)for k in ['id','status','assignee','labels']})
gate=json.loads((D/'gate-admission.json').read_text())
assert gate['passed'] is True and gate['physical_handoff_stopped'] is True,'GATE_NOT_PASSED_OR_NOT_STOPPED'
assert hashlib.sha256(Path(gate['gate_path']).read_bytes()).hexdigest()==gate['gate_SHA256'],'GATE_SOURCE_CHANGED'
for f,h in gate['input_bindings_SHA256'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,'GATE_INPUT_BINDING_CHANGED'
assert c['NN_cap']==307200 and c['job_seconds']==300 and c['science_deadline']=='2026-10-04T02:10:00Z','CONTRACT_CAPS_CHANGED'
current=[];foreign=[];researchRSS=0
for pid,row in table().items():
 if pid==os.getpid() or row['state']=='Z':continue
 try:args=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode();comm=Path(f'/proc/{pid}/comm').read_text().strip()
 except FileNotFoundError:continue
 if comm not in ['python','python3','node','bash','faithful-native']:continue
 if 'tools/ai-sigma-' not in args and 'tools/research-team/' not in args and 'faithful-native' not in args and '.artifacts/ai-sigma/continuation-20261001/' not in args and 'tools/nnue-training/' not in args and 'research-data/ai-sigma/frame14-' not in args:continue
 if str(T) in args:continue
 aff=sorted(os.sched_getaffinity(pid));researchRSS+=row['RSS'];current.append({**row,'affinity':aff,'argv':args[:220]})
 if any(k in args for k in ['ort.py','provider.py','learn.py','learn-control.cjs','runner.py','generate.cjs','measure.cjs','faithful-native','engine.cjs','tools/nnue-training/train.py','tools/nnue-training/evaluate.py','tools/ai-sigma-frame14','run.py','launch.py','tools/ai-sigma-qf1-distance-residual']):foreign.append(current[-1])
if c['kind']!='mock':assert not foreign,('EXTERNAL_HEAVY',foreign)
scheduler=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');sch=json.loads(scheduler.read_text());next_at=sch['next_at'];assert isinstance(next_at,(int,float)) and sch.get('phase') not in ['stopped','failed'],'SUPERVISOR_FRAME14_BINDING_UNKNOWN';assert not sch.get('recovery_required'),'SUPERVISOR_OWNER_UNKNOWN'
if c['management_core']==0:assert sch.get('owned') is None and next_at-time.time()>c['job_seconds']+30,'SUPERVISOR_QUIETWINDOW_SHORT'
gpu_current=[]
if c['mode'].startswith('GPU') or c['kind']=='parity':
 z=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,timeout=5,check=True);gpu_current=z.stdout.splitlines();assert not gpu_current,('EXTERNAL_GPU_CURRENT_UNKNOWN',gpu_current)
binding=json.loads((D/'binding.json').read_text())
for f,h in binding['readonly'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,'READONLY_BINDING_CHANGED'
assert researchRSS+c['RAM']<=8*1024**3,'PARENT_RAM';available=int(next(s.split()[1]for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:')))*1024;assert available>c['RAM'],'HOST_RAM'
# Retain all old physical quantities; compare current referenced experiment roots plus new forecast.
oldnames=['NATIVE-BASELINE','NATIVE-RUNTIME-READY','NATIVE-NI-ARENA','NATIVE-TEACHER-PIPELINE','NATIVE-K800-TIME','CHECKPOINT-TEACHER','MANYGAME-GENERATION']
old=allocated([ROOT/'.artifacts/ai-sigma/resume-20261003'/n for n in oldnames]+[ROOT/'research-data/ai-sigma'/n for n in ['165-native-baseline','170-native-runtime-ready','173-native-ni-arena','176-native-teacher-pipeline','180-native-k800-time','181-checkpoint-teacher','185-manygame-runtime-preparation','187-manygame-generation']]+[ROOT/'tools'/n for n in ['ai-sigma-native-baseline','ai-sigma-native-runtime-ready','ai-sigma-native-ni-arena','ai-sigma-native-teacher-pipeline','ai-sigma-native-k800-time','ai-sigma-native-checkpoint-teacher','ai-sigma-manygame-runtime-preparation','ai-sigma-manygame-generation']]);old+=allocated([ROOT/'research-data/ai-sigma/frame14-teachers',ROOT/'tools/ai-sigma-frame14-teachers',ROOT/'.artifacts/ai-sigma/frame14-teachers',ROOT/'research-data/ai-sigma/frame14-l2-test',ROOT/'tools/ai-sigma-frame14-l2-test']);assert old+32*1024**2<1980*1024**2,'EXPERIMENT_RESERVATION'
assert allocated([T,D,A])+8*1024**2<28*1024**2,'FORECAST_GUARD'
source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in T.iterdir()if p.is_file()}
save('admission.json',{'UTC':utc(),'controls':controls,'current':current,'foreign_heavy':foreign,'scheduler':sch,'quietwindow_seconds':next_at-time.time(),'known_old_allocated':old,'scope_allocated':allocated([T,D,A]),'newforecast':32*1024**2,'Git_forecast':8*1024**2,'reservation':1980*1024**2,'old_unknown_not_decremented':True,'RAM':c['RAM'],'RAMguard':c['RAM_guard'],'parent_current_RSS':researchRSS,'CPU_pool':c['cores'],'source':source,'prior_job_seconds':prior,'GPU_current':gpu_current,'sampled_not_all_host_guarantee':True})
cmd=['node','--max-old-space-size=192',str(T/c['script']),str(out)if c['kind']in ['mock','parity'] else str(Path(sys.argv[1]).resolve())]
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',SIGMA_SOURCE=c['source_git'])
tracked={};reason=None;peak=0;storagepeak=0;child=None;startUTC=utc();limit=min(time.time()+c['job_seconds'],end(c['science_deadline']),time.time()+360-prior)
with (out/'stdout.txt').open('w')as log:
 child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);first=table()[child.pid];tracked[(child.pid,first['tick'])]=first
 def group():
  tab=table();active={p for p,t in tracked if tab.get(p,{}).get('tick')==t};active|={p for p,x in tab.items()if x['ppid']==os.getpid()};changed=True
  while changed:
   new={p for p,x in tab.items()if x['ppid']in active};changed=not new<=active;active|=new
  for p in active:
   if p in tab:tracked[(p,tab[p]['tick'])]=tab[p]
  return [tab[p]for p in active if p in tab]
 def kill(sig):
  for x in group():
   if x['state']!='Z':
    try:
     if table().get(x['pid'],{}).get('tick')==x['tick']:os.kill(x['pid'],sig)
    except ProcessLookupError:pass
 while child.poll()is None:
  members=group();rss=sum(x['RSS']for x in members)+table()[os.getpid()]['RSS'];peak=max(peak,rss);used=allocated([T,D,A]);storagepeak=max(storagepeak,used)
  for x in members:
   try:
    for tid in Path(f'/proc/{x["pid"]}/task').iterdir():
     aff=sorted(os.sched_getaffinity(int(tid.name)))
     if len(aff)!=1 or aff[0]not in c['cores']:reason='AFFINITY_UNKNOWN'
   except (FileNotFoundError,ProcessLookupError):pass
  if rss>=c['RAM_guard']:reason='RAM_GUARD'
  if used+8*1024**2>=28*1024**2:reason='STORAGE_GUARD'
  if time.time()>=limit:reason='JOB_OR_SCIENCE_OR_TOTAL_DEADLINE'
  if (out/'PAUSE').exists():reason='PAUSED'
  if reason:break
  time.sleep(.1)
 if reason:kill(signal.SIGTERM)
 try:code=child.wait(timeout=2)
 except subprocess.TimeoutExpired:kill(signal.SIGKILL);code=child.wait(timeout=2)
 for x in group():
  if x['state']!='Z':
   try:os.kill(x['pid'],signal.SIGKILL)
   except ProcessLookupError:pass
 for _ in range(200):
  try:
   pid,status=os.waitpid(-1,os.WNOHANG)
   if pid==0:time.sleep(.005)
  except ChildProcessError:break
remaining=group();receipt={'issue':c['issue'],'run':name,'kind':c['kind'],'mode':c.get('mode'),'startUTC':startUTC,'endUTC':utc(),'jobwall_seconds':time.monotonic()-wall,'exit':code,'stop_reason':reason,'runner_pid':os.getpid(),'runner_tick':table()[os.getpid()]['tick'],'tracked':list(tracked.values()),'remaining':remaining,'peak_aggregate_RSS':peak,'peak_allocated_scope':storagepeak,'final_allocated_scope':allocated([T,D,A]),'command':cmd,'source_git':c['source_git'],'NN_cap':c['NN_cap'],'instant_peak_not_guaranteed':True}
save('process.json',receipt);print(json.dumps({k:v for k,v in receipt.items()if k not in ['tracked','command']}));sys.exit(0 if code==0 and not reason and not remaining else 1)
