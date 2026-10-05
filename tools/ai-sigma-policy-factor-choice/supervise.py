import os,sys,time,json,subprocess,resource,datetime,signal,hashlib
from pathlib import Path
ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma');OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/POLICY-FACTOR-CHOICE';TOOL=ROOT/'tools/ai-sigma-policy-factor-choice';DATA=ROOT/'research-data/ai-sigma/136-policy-factor-choice';intake=json.loads((DATA/'intake.json').read_text());name=sys.argv[1];assert not (OUT/(name+'.started.json')).exists();assert time.time()<datetime.datetime.fromisoformat(intake['new_command_cutoff']).timestamp();assert sum(json.loads(p.read_text())['elapsed_s'] for p in OUT.glob('*.process.json'))<180,'TOTAL_RUNTIME';os.sched_setaffinity(0,{0});resource.setrlimit(resource.RLIMIT_CORE,(0,0));tmp=OUT/'temp';tmp.mkdir(exist_ok=True)
def ident(pid):
 s=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split();return {'PID':pid,'ppid':int(s[1]),'PGID':int(s[2]),'starttick':int(s[19]),'rss':int(s[21])*4096}
def ownsize():
 return sum(p.stat().st_blocks*512 for b in [OUT,TOOL,DATA] for p in b.rglob('*') if p.is_file())+ (ROOT/'docs/reports/ai-sigma-hypothesis-policy-factor-choice.md').stat().st_blocks*512
def size():
 return 8073216+ownsize() # prior observed holding conservatively retained; no old amount deducted

env=os.environ.copy();env.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),XDG_CACHE_HOME=str(tmp),XDG_CONFIG_HOME=str(tmp),UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',SIGMA_POLICY_RUN=name);cmd=sys.argv[2:];start=time.time();mono=time.monotonic();end=min(start+60,datetime.datetime.fromisoformat(intake['processing_deadline']).timestamp(),start+180-sum(json.loads(p.read_text())['elapsed_s'] for p in OUT.glob('*.process.json')));boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();parent=ident(os.getpid());peak=0;usedpeak=0;TIDs={};descendants={};reason=None;observations=0;child_identity=None
with (OUT/(name+'.log')).open('wb') as log:
 c=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);child_identity=ident(c.pid);(OUT/(name+'.started.json')).write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonic':mono,'boot':boot,'parent':parent,'child':child_identity,'command':cmd,'command_sha256':hashlib.sha256(json.dumps(cmd).encode()).hexdigest(),'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in TOOL.iterdir() if p.is_file()},'deadline_epoch':end,'memory':'Nodeheap192 + sampled parent/child RSS896MiB; no AS limit','TMP':str(tmp)},indent=2)+'\n')
 while c.poll() is None:
  try:
   a=ident(c.pid);assert a['starttick']==child_identity['starttick'];owned=[a];pending=[c.pid]
   while pending:
    z=pending.pop()
    try:children=Path(f'/proc/{z}/task/{z}/children').read_text().split()
    except FileNotFoundError:continue
    for kid in children:
     try:k=ident(int(kid));descendants[k['PID']]=k;owned.append(k);pending.append(k['PID'])
     except FileNotFoundError:pass
   rss=sum(k['rss'] for k in owned)+ident(os.getpid())['rss'];peak=max(peak,rss);used=size();usedpeak=max(usedpeak,used);observations+=1
   for task in [task for own in owned if Path(f"/proc/{own['PID']}/task").exists() for task in Path(f"/proc/{own['PID']}/task").iterdir()]:
    try:aff=sorted(os.sched_getaffinity(int(task.name)));TIDs[int(task.name)]=aff;assert aff==[0],'AFFINITY'
    except ProcessLookupError:pass
   assert rss<939524096,'RSS_GUARD';assert used<14680064,'STORAGE_GUARD';assert ownsize()<2097152,'OWN_STORAGE_TARGET';assert time.time()<end,'DEADLINE'
  except FileNotFoundError:
   if c.poll() is None:reason='process_observation_race'
   break
  except Exception as e:reason=str(e);break
  time.sleep(.02)
 if reason and c.poll() is None:
  current=ident(c.pid)
  if current['starttick']==child_identity['starttick']:os.killpg(c.pid,signal.SIGTERM)
 try:code=c.wait(timeout=2)
 except subprocess.TimeoutExpired:
  current=ident(c.pid);assert current['starttick']==child_identity['starttick'];os.killpg(c.pid,signal.SIGKILL);code=c.wait(timeout=2);reason=reason or 'termination_timeout'
remaining=[]
try:
 v=ident(c.pid)
 if v['starttick']==child_identity['starttick']:remaining.append(v)
except FileNotFoundError:pass
stop={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonic':time.monotonic(),'elapsed_s':time.monotonic()-mono,'parent':parent,'child':child_identity,'descendants':list(descendants.values()),'exit':code,'guard_error':reason,'remaining':remaining,'PID0':not remaining,'parent_plus_child_RSS_max':peak,'sample20ms':True,'observations':observations,'TID_affinity':TIDs,'allocated_peak':usedpeak,'allocated_final':size(),'child_CPU_seconds':resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,'parent_CPU_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,'short_lived_TIDs_or_instant_peak_unobserved':True,'NN':0,'engine':0,'games':0};(OUT/(name+'.process.json')).write_text(json.dumps(stop,indent=2)+'\n');print(json.dumps(stop));sys.exit(code if code else (1 if reason else 0))
