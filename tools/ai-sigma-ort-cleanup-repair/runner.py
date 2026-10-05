import os,sys,json,time,signal,subprocess,datetime,resource,ctypes,hashlib
from pathlib import Path
TOOL=Path(__file__).resolve().parent;OUT=TOOL.parents[1]/'.artifacts/ai-sigma/runs/SIGMA-ORT-CLEANUP-REPAIR';END=datetime.datetime.fromisoformat('2026-10-01T11:25:00+00:00').timestamp()
assert time.time()<END-300,'NEW_JOB_CUTOFF'
name=sys.argv[1];cmd=sys.argv[2:];os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_CORE,(0,0));ctypes.CDLL(None).prctl(36,1,0,0,0)
for d in ['t','xdg-cache','xdg-config']:(OUT/d).mkdir(exist_ok=True)
os.chdir(OUT);alias=f'/proc/{os.getpid()}/cwd/t';assert Path(alias).resolve()==OUT/'t'
env=os.environ.copy();env.update(TMPDIR=alias,TMP=alias,TEMP=alias,XDG_CACHE_HOME=str(OUT/'xdg-cache'),XDG_CONFIG_HOME=str(OUT/'xdg-config'),UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',PLAYWRIGHT_BROWSERS_PATH='/workspaces/quoridor/artifacts/playwright')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def storage():
 seen=set();total=0
 for base in (TOOL,OUT):
  for p in base.rglob('*'):
   try:
    if p.is_file():
     z=p.stat();key=(z.st_dev,z.st_ino)
     if key not in seen:seen.add(key);total+=z.st_blocks*512
   except (FileNotFoundError,ProcessLookupError):pass
 return total
def table():
 r={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:s=(p/'stat').read_text().rsplit(')',1)[1].split();r[int(p.name)]={'pid':int(p.name),'ppid':int(s[1]),'pgid':int(s[2]),'start_ticks':int(s[19]),'state':s[0],'rss':int(s[21])*4096}
  except (OSError,ValueError,IndexError):pass
 return r
trace=OUT/(name+'.monitor.jsonl')
def event(kind,**data):
 with trace.open('a') as f:f.write(json.dumps({'kind':kind,'UTC':utc(),'monotonic':time.monotonic(),**data})+'\n')
tracked={};child=None;childtick=None;reason=None;peak=0;sizepeak=0;start=utc()
def group():
 t=table();known={pid for (pid,tick) in tracked if t.get(pid,{}).get('start_ticks')==tick}
 if child and t.get(child.pid,{}).get('start_ticks')==childtick:known.add(child.pid)
 more=True
 while more:
  additions={p for p,v in t.items() if v['ppid'] in known or (v['pgid']==child.pid and any(t[k]['pgid']==child.pid for k in known if k in t))}
  more=not additions<=known;known|=additions
 for pid in known:
  if pid not in t:continue
  v=t[pid];key=(pid,v['start_ticks']);r=tracked.setdefault(key,{**v,'maxrss':0,'affinities':[],'TID_samples':0})
  r['maxrss']=max(r['maxrss'],v['rss']);r['last_ppid']=v['ppid'];r['last_state']=v['state']
  try:
   for task in Path(f'/proc/{pid}/task').iterdir():
    affinity=sorted(os.sched_getaffinity(int(task.name)));r['TID_samples']+=1
    if affinity not in r['affinities']:r['affinities'].append(affinity)
    if affinity!=[2]:raise RuntimeError('AFFINITY_GUARD')
  except (FileNotFoundError,ProcessLookupError):pass
 return [t[p] for p in known if p in t]
def kill_owned(sig):
 for v in group():
  if v['state']=='Z':continue
  try:
   current=table().get(v['pid']);
   if current and current['start_ticks']==v['start_ticks']:os.kill(v['pid'],sig)
  except ProcessLookupError:pass
def reap_adopted():
 for v in group():
  if v['pid']==child.pid or v['ppid']!=os.getpid():continue
  try:
   current=table().get(v['pid'])
   if not current or current['start_ticks']!=v['start_ticks'] or current['ppid']!=os.getpid():
    event('adopted_wait_identity_refused',expected=v,actual=current);continue
   outcome=os.waitpid(v['pid'],os.WNOHANG)
   if outcome[0] or v['state']=='Z':event('adopted_wait',identity=v,outcome=outcome)
  except ChildProcessError:event('adopted_wait_echild',identity=v)
interrupted=None
def signal_stop(sig,frame):
 global interrupted
 interrupted=f'signal{sig}'
signal.signal(signal.SIGTERM,signal_stop);signal.signal(signal.SIGINT,signal_stop)
import shutil
snapshot=OUT/'job-source'/name;snapshot.mkdir(parents=True,exist_ok=False)
for source in TOOL.iterdir():
 if source.is_file() and source.suffix in ['.py','.cjs','.js']:shutil.copyfile(source,snapshot/source.name)
(OUT/(name+'.inputs.json')).write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()},indent=2)+'\n')
with (OUT/(name+'.log')).open('wb') as log:
 child=subprocess.Popen(cmd,cwd=TOOL,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 childtick=table().get(child.pid,{}).get('start_ticks');deadline=min(END,time.time()+120)
 (OUT/(name+'.started.json')).write_text(json.dumps({'runner_pid':os.getpid(),'runner_starttick':table()[os.getpid()]['start_ticks'],'child_pid':child.pid,'child_starttick':childtick,'PGID':child.pid,'startUTC':start,'command':cmd,'cwd':str(TOOL),'deadline':deadline,'affinity':[2],'guardRSS':3758096384,'guardStorage':117440512,'temp':alias,'temp_realpath':str(Path(alias).resolve())},indent=2)+'\n')
 event('runner_start',root_child_pid=child.pid,root_child_starttick=childtick,runner_pid=os.getpid(),subreaper=True)
 while child.poll() is None:
  cycle_start=time.monotonic()
  try:members=group();reap_adopted();rss=sum(x['rss'] for x in members)+resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;used=storage();peak=max(peak,rss);sizepeak=max(sizepeak,used)
  except Exception as e:reason=str(e);break
  if interrupted:reason=interrupted
  elif time.time()>=deadline:reason='deadline'
  elif rss>=3758096384:reason='RSS_GUARD'
  elif used>=117440512:reason='STORAGE_GUARD'
  if reason:break
  if any(v['state']=='Z' for v in members):event('monitor_zombies',members=[v for v in members if v['state']=='Z'])
  event('monitor_cycle',elapsed_seconds=time.monotonic()-cycle_start,member_count=len(members),RSS=rss,storage=used)
  time.sleep(.02)
 if reason:
  kill_owned(signal.SIGTERM)
  try:child.wait(timeout=2)
  except subprocess.TimeoutExpired:kill_owned(signal.SIGKILL);child.wait(timeout=2)
 code=child.wait()
 for _ in range(100):
  reap_adopted();residual=group()
  if not residual:break
  kill_owned(signal.SIGKILL);time.sleep(.01)
 remaining=group()
r={'name':name,'cmd':cmd,'start':start,'end':utc(),'runner_pid':os.getpid(),'runner_starttick':table()[os.getpid()]['start_ticks'],'child_pid':child.pid,'child_starttick':childtick,'exit':code,'stop_reason':reason,'sample_interval_ms':20,'peak_group_plus_runner_RSS':peak,'peak_allocated_bytes':sizepeak,'final_allocated_bytes':storage(),'tracked':list(tracked.values()),'remaining':remaining,'privateTMP_alias':alias,'privateTMP_realpath':str(Path(alias).resolve()),'process_deadline':'11:25Z','newjob_cutoff':'11:20Z','all_observed_TIDs_CPU2':not any(z!=[2] for x in tracked.values() for z in x['affinities']),'instant_peak_not_guaranteed':True,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/(name+'.process.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['name','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','remaining']}));sys.exit(code if code>=0 else 128-code)
