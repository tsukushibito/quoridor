import os,sys,json,time,subprocess,signal,datetime,pathlib,hashlib,resource
ROOT=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-puct-factor');RUN=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma/.artifacts/ai-sigma/runs/SIGMA-PUCT-FACTOR');CACHE=pathlib.Path('/home/vscode/.cache/inference/research/ai-sigma/puct-factor')
END=datetime.datetime.fromisoformat('2026-10-01T03:30:00+00:00').timestamp();GUARD=3758096384
assert time.time()<datetime.datetime.fromisoformat('2026-10-01T03:25:00+00:00').timestamp(),'NEW_JOB_DEADLINE';name=sys.argv[1];cmd=sys.argv[2:];allowed={2,4} if "build" in name or name.startswith("lock-") else {2};os.sched_setaffinity(0,allowed);(CACHE/'temp').mkdir(exist_ok=True);import fcntl;lock=(CACHE/'job.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
env=os.environ.copy();env.update(CARGO_HOME='/home/vscode/.cache/inference/research/ai-sigma/ort-search/cargo-home',CARGO_TARGET_DIR=str(CACHE/'target'),CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE',MKL_NUM_THREADS='1',MKL_DYNAMIC='FALSE',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=f'/proc/{os.getpid()}/cwd',TMP=f'/proc/{os.getpid()}/cwd',TEMP=f'/proc/{os.getpid()}/cwd',XDG_CACHE_HOME=str(CACHE/'browser-cache'),XDG_CONFIG_HOME=str(CACHE/'browser-config'),UV_NO_SYNC='1',UV_OFFLINE='1',PLAYWRIGHT_BROWSERS_PATH='/workspaces/quoridor/artifacts/playwright',LIBGL_ALWAYS_SOFTWARE='1')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def size():
 total=0;seen=set()
 for root in (ROOT,RUN,CACHE):
  for parent,dirs,files in os.walk(root):
   for name in files:
    try:
     z=os.stat(os.path.join(parent,name));key=(z.st_dev,z.st_ino)
     if key not in seen:seen.add(key);total+=z.st_size
    except (FileNotFoundError,ProcessLookupError):pass
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
    if not set(cp).issubset(allowed):
     z.setdefault('affinity_corrections',[]).append({'thread':int(t.name),'observed':cp});os.sched_setaffinity(int(t.name),allowed)
    if cp not in z['affinities']:z['affinities'].append(cp)
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
  out.append((pid,rss))
 return out
def stop_owned(sig):
 for pid,_ in reversed(group()):
  try:os.kill(pid,sig)
  except ProcessLookupError:pass
model=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma/models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx');assert hashlib.sha256(model.read_bytes()).hexdigest()=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d';job_end=min(END,time.time()+(180 if "build" in name else 4200 if name=="matches-execution" else 120));os.chdir(CACHE/"temp");assert pathlib.Path(env['TMPDIR']).resolve()==CACHE/'temp';import shutil;snapshot=RUN/'job-source'/name;snapshot.mkdir(parents=True,exist_ok=False)
for source in ROOT.rglob('*'):
 if source.is_file() and source.suffix in ('.rs','.js','.cjs','.py','.toml','.lock'):
  dst=snapshot/source.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dst)
source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.rs','.js','.cjs','.py','.toml','.lock')};source_hashes['B_wasm']=hashlib.sha256((CACHE/'target/wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm').read_bytes()).hexdigest() if (CACHE/'target/wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm').exists() else None;source_hashes['A_wasm']=hashlib.sha256((ROOT/'../../.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH/final.wasm').read_bytes()).hexdigest();(RUN/(name+'.inputs.json')).write_text(json.dumps(source_hashes,indent=2)+'\n');start=utc();baseline=size();log=RUN/(name+'.log');peak=0;peaksize=baseline;reason=None
with log.open('wb') as f:
 child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 info={'host_load_start':pathlib.Path('/proc/loadavg').read_text(),'cpu_stat_start':pathlib.Path('/proc/stat').read_text(),'name':name,'runner_pid':os.getpid(),'pid':child.pid,'pgid':child.pid,'start':start,'cmd':cmd,'affinity':sorted(allowed),'baseline_bytes':baseline,'runner_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'NN_OUT_TAG':os.environ.get('NN_OUT_TAG',''),'deadline':END,'temporary_alias':env['TMPDIR'],'temporary_alias_resolved':str(pathlib.Path(env['TMPDIR']).resolve()),'job_end':job_end};(RUN/(name+'.process.json')).write_text(json.dumps(info,indent=2))
 while child.poll() is None:
  members=group();rss=sum(r for _,r in members)+resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;info.setdefault('start_group_plus_runner_rss_bytes',rss);peak=max(peak,rss);used=size();peaksize=max(peaksize,used)
  if time.time()>=min(END,job_end):reason='processing_deadline'
  elif rss>=GUARD:reason='rss_guard'
  elif used>=234881024 or 3782000000+used>=int(4.85*1024**3):reason='storage_guard'
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
info.update(host_load_end=pathlib.Path('/proc/loadavg').read_text(),cpu_stat_end=pathlib.Path('/proc/stat').read_text(),end=utc(),exit=rc,stop_reason=reason,peak_group_plus_runner_rss_bytes=peak,peak_storage_bytes=peaksize,final_storage_bytes=size(),remaining_pids=group(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),children_usage={'user_s':resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime,'system_s':resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,'maxrss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss})
info.update(processing_deadline_utc='2026-10-01T03:30:00Z',checkpoint=None,prior_experiment_bytes=3782000000,owned_storage_bytes_conservative=3782000000+size(),tracked_processes=list(tracked.values()),tracked_cpu_seconds=sum(x['max_cpu_ticks'] for x in tracked.values())/os.sysconf('SC_CLK_TCK'),temporary_roots=[str(CACHE/'temp'),str(CACHE/'browser-cache')]);(RUN/(name+'.process.json')).write_text(json.dumps(info,indent=2)+'\n');print(json.dumps({k:v for k,v in info.items() if k in ['name','pid','pgid','start','end','exit','stop_reason','peak_group_plus_runner_rss_bytes','peak_storage_bytes','final_storage_bytes','remaining_pids','owned_storage_bytes_conservative']}));sys.exit(rc if rc>=0 else 128-rc)
