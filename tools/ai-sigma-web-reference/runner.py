import os,sys,json,time,subprocess,signal,datetime,pathlib,hashlib,resource
ROOT=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-web-reference');RUN=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma/.artifacts/ai-sigma/runs/SIGMA-WEB-REFERENCE');CACHE=pathlib.Path('/home/vscode/.cache/inference/research/ai-sigma/web-reference')
END=datetime.datetime.fromisoformat('2026-09-30T21:51:46+00:00').timestamp();GUARD=1879048192
name=sys.argv[1];cmd=sys.argv[2:];os.sched_setaffinity(0,{0});(CACHE/'t').mkdir(exist_ok=True);(ROOT/'t').mkdir(exist_ok=True);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
env=os.environ.copy();env.update(CARGO_HOME=str(CACHE/'cargo-home'),CARGO_TARGET_DIR=str(CACHE/'target'),CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE',MKL_NUM_THREADS='1',MKL_DYNAMIC='FALSE',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=f'/proc/{os.getpid()}/cwd/t',TMP=f'/proc/{os.getpid()}/cwd/t',TEMP=f'/proc/{os.getpid()}/cwd/t',XDG_CACHE_HOME=str(CACHE/'browser-cache'),XDG_CONFIG_HOME=str(CACHE/'browser-config'),UV_NO_SYNC='1',UV_OFFLINE='1')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def size():
 total=0;seen=set()
 for root in (ROOT,RUN,CACHE,pathlib.Path("/workspaces/quoridor/.worktree/ai-sigma/.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE")):
  for p in root.rglob('*'):
   try:
    if p.is_file():
     z=p.stat();key=(z.st_dev,z.st_ino)
     if key not in seen:seen.add(key);total+=z.st_size
   except FileNotFoundError:pass
 return total
tracked={}; identities={}
def group():
 table={}
 for p in pathlib.Path('/proc').iterdir():
  if p.name.isdigit():
   try:
    s=(p/'stat').read_text().rsplit(')',1)[1].split();table[int(p.name)]=(int(s[1]),int(s[2]),int(s[19]),int(s[21])*os.sysconf('SC_PAGE_SIZE'),int(s[11])+int(s[12]))
   except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 known={pid for pid,start in identities.items() if pid in table and table[pid][2]==start};known.add(child.pid)
 change=True
 while change:
  added={pid for pid,v in table.items() if v[0] in known or v[1]==child.pid};change=not added.issubset(known);known|=added
 out=[]
 for pid in known:
  if pid not in table:continue
  pp,pg,st,rss,ticks=table[pid];identities[pid]=st
  if pid not in tracked:tracked[pid]={'pid':pid,'start_ticks':st,'pgid':pg,'maxrss_bytes':0,'max_cpu_ticks':0,'max_threads':0,'affinities':[]}
  z=tracked[pid];z['maxrss_bytes']=max(z['maxrss_bytes'],rss);z['max_cpu_ticks']=max(z['max_cpu_ticks'],ticks)
  try:
   tasks=list(pathlib.Path(f'/proc/{pid}/task').iterdir());z['max_threads']=max(z['max_threads'],len(tasks))
   for t in tasks:
    cp=sorted(os.sched_getaffinity(int(t.name)))
    if cp not in z['affinities']:z['affinities'].append(cp)
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
  out.append((pid,rss))
 return out
def stop_owned(sig):
 for pid,_ in reversed(group()):
  try:os.kill(pid,sig)
  except ProcessLookupError:pass
model=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma/models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx');assert hashlib.sha256(model.read_bytes()).hexdigest()=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d';job_end=time.time()+(120);os.chdir(CACHE);assert pathlib.Path(env['TMPDIR']).resolve()==CACHE/'t';start=utc();baseline=size();log=RUN/(name+'.log');peak=0;peaksize=baseline;reason=None
with log.open('wb') as f:
 child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 info={'name':name,'runner_pid':os.getpid(),'pid':child.pid,'pgid':child.pid,'start':start,'cmd':cmd,'affinity':[0],'baseline_bytes':baseline,'deadline':END,'temporary_alias':env['TMPDIR'],'temporary_alias_resolved':str(pathlib.Path(env['TMPDIR']).resolve()),'job_end':job_end};(RUN/(name+'.process.json')).write_text(json.dumps(info,indent=2))
 while child.poll() is None:
  members=group();rss=sum(r for _,r in members)+resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;peak=max(peak,rss);used=size();peaksize=max(peaksize,used)
  if time.time()>=min(END,job_end):reason='processing_deadline'
  elif any(cp != [0] for x in tracked.values() for cp in x['affinities']):reason='affinity_guard'
  elif rss>=GUARD:reason='rss_guard'
  elif used>=469762048:reason='storage_guard'
  if reason:
   stop_owned(signal.SIGTERM)
   try:child.wait(timeout=3)
   except subprocess.TimeoutExpired:stop_owned(signal.SIGKILL);child.wait()
   break
  time.sleep(.05)
 rc=child.wait()
 # stop any surviving members of this own group
 residual=group()
 if residual:
  stop_owned(signal.SIGTERM);time.sleep(.05)
  if group():stop_owned(signal.SIGKILL)
info.update(end=utc(),exit=rc,stop_reason=reason,peak_group_plus_runner_rss_bytes=peak,peak_storage_bytes=peaksize,final_storage_bytes=size(),remaining_pids=group(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),children_usage={'user_s':resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime,'system_s':resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,'maxrss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss})
info.update(tracked_processes=list(tracked.values()),tracked_cpu_seconds=sum(x['max_cpu_ticks'] for x in tracked.values())/os.sysconf('SC_CLK_TCK'),temporary_roots=[str(CACHE/'t'),str(CACHE/'browser-cache'),str(CACHE/'browser-config')]);(RUN/(name+'.process.json')).write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info));sys.exit(rc if rc>=0 else 128-rc)
