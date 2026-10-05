"""CPU2 NN0 admission/guardian. No inference dependencies are imported."""
import ctypes,datetime,hashlib,json,os,pathlib,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[2];T=pathlib.Path(__file__).resolve().parent
D=ROOT/'research-data/ai-sigma/185-manygame-runtime-preparation';D.mkdir(exist_ok=True)
name=sys.argv[1];assert name.startswith('native185-') and '/' not in name
OUT=D/'runs'/name;assert not OUT.exists(),'ATTEMPT_ALREADY_EXISTS';OUT.mkdir(parents=True)
start=time.monotonic();utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-03T12:12:00+00:00'),'NEW_COMMAND_CUTOFF'
assert time.time()-datetime.datetime.fromisoformat('2026-10-03T11:44:15+00:00').timestamp()<35*60,'RECEIPT_WINDOW'
os.sched_setaffinity(0,{2});libc=ctypes.CDLL(None);assert libc.prctl(36,1,0,0,0)==0
def write(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def tables():
 out={}
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   s=(p/'stat').read_text().rsplit(')',1)[1].split();out[int(p.name)]={'pid':int(p.name),'ppid':int(s[1]),'tick':int(s[19]),'state':s[0],'RSS':int(s[21])*4096}
  except (FileNotFoundError,ProcessLookupError):pass
 return out
def allocated():
 seen=set();s=0
 for base in [D,T]:
  for p in base.rglob('*'):
   if p.is_file():
    x=p.stat();k=(x.st_dev,x.st_ino)
    if k not in seen:seen.add(k);s+=x.st_blocks*512
 return s
prior=list((D/'runs').glob('*/process.json'));past=sum(json.loads(p.read_text())['jobwall_seconds']for p in prior)
assert past<180
used=sum(json.loads(p.read_text()).get('mock_reply_upper_bound',0)for p in prior)
reply_upper=int(os.environ.get('NN0_REPLY_UPPER','384'));assert used+reply_upper<=512
controls={}
for issue in ['quoridor-4lc','quoridor-4lc.185']:
 x=subprocess.run(['bash',str(ROOT/'scripts/dev/beads.sh'),'show',issue,'--json'],capture_output=True,text=True,timeout=10,check=True);j=json.loads(x.stdout)[0]
 assert j['status']=='in_progress' and 'paused-by-user' not in j.get('labels',[]),'CONTROL_OR_PAUSE_UNKNOWN'
 if issue.endswith('.185'):assert j['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746'
 controls[issue]={k:j.get(k)for k in ['id','status','assignee','labels','updated_at']}
stop=json.loads((ROOT/'research-data/ai-sigma/181-checkpoint-teacher/handoff-stop.json').read_text());assert stop['source_writer_stopped'] and stop['science_children_reaped'] and stop['backup_sync_exit']==0
foreign=[];researchRSS=0
tab=tables()
for pid,row in tab.items():
 if pid==os.getpid():continue
 try:args=(pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode());comm=(pathlib.Path(f'/proc/{pid}/comm').read_text().strip())
 except FileNotFoundError:continue
 if comm not in ['node','python','python3','faithful-native','bash']:continue
 if '/tools/ai-sigma-' not in args and '/tools/ai-sigma-' not in str(row):continue
 researchRSS+=row['RSS'];aff=sorted(os.sched_getaffinity(pid))
 if str(T) in args:continue
 if any(x in args for x in ['ort.py','provider.py','learn.py','runner.py','generate.cjs','measure.cjs']):foreign.append({'pid':pid,'affinity':aff,'argv':args[:300]})
assert not foreign,foreign
for p in (ROOT/'.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER/runs').glob('*.process.json'):
 j=json.loads(p.read_text())
 for pid,tick in [(j['runner_pid'],j['runner_starttick'])]+[(x['pid'],x['start_ticks'])for x in j['tracked']]:assert tab.get(pid,{}).get('tick')!=tick,'OLD_181_IDENTITY_ACTIVE'
assert researchRSS+1024**3<=8*1024**3 and allocated()+2*1024**2<7*1024**2
admission={'UTC':utc(),'controls':controls,'CPU':[2],'RAM':1024**3,'guard':896*1024**2,'foreign_heavy':foreign,'current_foreign_researchRSS':researchRSS,'scope_allocated':allocated(),'forecast':8*1024**2,'effective_experiment_reservation':2044*1024**2,'old_unknown_not_decremented':True,'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in T.iterdir()if p.is_file()},'prior_job_seconds':past,'reply_upper_bound':reply_upper,'prior_reply_upper_bound':used}
# Latest owner reservation is conservative; scope reuses existing experiment unused capacity.
old=json.loads((ROOT/'.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER/runs/native181-learn-r1.admission.json').read_text());admission['previous_known_old_allocated']=old.get('known_old_allocated');assert old.get('known_old_allocated',0)+old.get('forecast',0)+8*1024**2<=2044*1024**2
write('admission.json',admission)
command=['node','--max-old-space-size=192',str(T/sys.argv[2]),str(OUT)];tracked={};peak=0;reason=None;child=None
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
with (OUT/'stdout.txt').open('w')as log:
 child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);initial=tables()[child.pid];tracked[(child.pid,initial['tick'])]=initial
 def group():
  tab=tables();active={pid for pid,tick in tracked if tab.get(pid,{}).get('tick')==tick};active|={pid for pid,x in tab.items()if x['ppid']==os.getpid() and pid!=os.getpid()};changed=True
  while changed:
   new={pid for pid,x in tab.items()if x['ppid']in active};changed=not new<=active;active|=new
  for pid in active:
   if pid in tab:tracked[(pid,tab[pid]['tick'])]=tab[pid]
  return [tab[p]for p in active if p in tab]
 while child.poll()is None:
  members=group();rss=sum(x['RSS']for x in members)+tables()[os.getpid()]['RSS'];peak=max(peak,rss)
  if any(sorted(os.sched_getaffinity(x['pid']))!=[2]for x in members if pathlib.Path(f'/proc/{x["pid"]}').exists()):reason='AFFINITY_UNKNOWN'
  if rss>896*1024**2:reason='RAM_GUARD'
  if allocated()>7*1024**2:reason='STORAGE_GUARD'
  if time.monotonic()-start>min(30,180-past):reason='JOB_OR_TOTAL_TIMEOUT'
  if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat('2026-10-03T12:15:00+00:00'):reason='HARD_DEADLINE'
  if reason:break
  time.sleep(.02)
 if reason:
  for x in group():
   if x['state']!='Z':
    try:os.kill(x['pid'],signal.SIGTERM)
    except ProcessLookupError:pass
  time.sleep(.05)
 code=child.wait(timeout=2)
 # Drain/reap any owned descendants left by a failed fixture/transport.
 for x in group():
  if x['state']!='Z':
   try:os.kill(x['pid'],signal.SIGKILL)
   except ProcessLookupError:pass
 for _ in range(100):
  try:
   pid,status=os.waitpid(-1,os.WNOHANG)
   if pid==0:time.sleep(.005)
  except ChildProcessError:break
remaining=group();result=OUT/'result.json';payload=json.loads(result.read_text())if result.exists()else{}
receipt={'issue':'quoridor-4lc.185','run':name,'UTC':utc(),'jobwall_seconds':time.monotonic()-start,'exit':code,'stop_reason':reason,'command':command,'runner_pid':os.getpid(),'tracked':list(tracked.values()),'remaining':remaining,'peak_aggregate_RSS':peak,'scope_allocated':allocated(),'mock_reply_upper_bound':payload.get('mock_reply_equivalents',reply_upper),'NN':0,'model_sessions':0,'GPU':0,'sampled_resource_limits_not_full_host_guarantee':True}
write('process.json',receipt);print(json.dumps({k:v for k,v in receipt.items()if k not in ['tracked','command']}));assert code==0 and not reason and not remaining
