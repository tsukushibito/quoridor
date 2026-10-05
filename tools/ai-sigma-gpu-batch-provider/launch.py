"""Finite physical admission; one owned Node/provider tree, subreaper+RSS guard."""
import os,sys,json,time,signal,subprocess,hashlib,datetime,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];T=Path(__file__).resolve().parent;D=ROOT/'research-data/ai-sigma/177-gpu-batch-provider';REG=json.loads((D/'preregister.json').read_text());S=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');BOOT=Path('/proc/sys/kernel/random/boot_id').read_text().strip();SELF=os.getpid();stop=False
signal.signal(signal.SIGTERM,lambda *_:globals().__setitem__('stop',True));signal.signal(signal.SIGINT,lambda *_:globals().__setitem__('stop',True))
assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0

def table():
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   f=(p/'stat').read_text().rsplit(')',1)[1].split();out[int(p.name)]={'pid':int(p.name),'ppid':int(f[1]),'pgid':int(f[2]),'starttick':f[19],'RSS':int(f[21])*4096,'state':f[0],'affinity':sorted(os.sched_getaffinity(int(p.name))),'cmd':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')[:600]}
  except (FileNotFoundError,ProcessLookupError):pass
 return out

def control():
 for issue in ['quoridor-4lc','quoridor-4lc.177']:
  r=subprocess.run(['bash',str(ROOT/'scripts/dev/beads.sh'),'show',issue,'--json'],capture_output=True,text=True,timeout=8);assert r.returncode==0,'CONTROL_READ'
  o=json.loads(r.stdout)[0];assert o['status']=='in_progress' and 'paused-by-user' not in o.get('labels',[]),'PAUSE'
  if issue.endswith('.177'):assert o['assignee']=='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418','OWNER'

def admit():
 now=time.time();assert now<REG['newheavy_epoch'] and now+210<REG['processing_epoch'],'DEADLINE'
 s=json.loads(S.read_text());assert s['phase']=='running' and not s['recovery_required'],'SCHEDULER_STATE';assert s['owned'] is None,'SUPERVISOR_OWNED';assert s['next_at']-now>210,'SUPERVISOR_WINDOW'
 tab=table();p=s['process'];assert p['boot_id']==BOOT and p['pid'] in tab and str(p['start_ticks'])==tab[p['pid']]['starttick'],'SCHEDULER_IDENTITY';assert hashlib.sha256(Path(s['config_path']).read_bytes()).hexdigest()==s['config_sha256'],'SCHEDULER_CONFIG'
 stopfile=ROOT/'research-data/ai-sigma/178-teacher-design/static-stop.json';assert stopfile.exists(),'178_STATIC_JOB_STOP_PENDING';cs=json.loads(stopfile.read_text());assert cs['science_source_stopped'] and cs['current_identity_absent'] and cs['mock_PID'] not in tab,'178_JOB_CURRENT'
 assert hashlib.sha256((ROOT/'research-data/ai-sigma/178-teacher-design/mock.py').read_bytes()).hexdigest()==cs['source_SHA256'],'178_STOP_SOURCE'
 anc={SELF};pid=SELF
 while pid in tab and pid>1:pid=tab[pid]['ppid'];anc.add(pid)
 selected=[r for r in tab.values() if r['pid'] not in anc and r['state']!='Z' and any(k in r['cmd'] for k in ['ai-sigma-','research-team','research-scheduler'])]
 for r in selected:
  if '178-teacher-design' in r['cmd']:raise AssertionError('178_NEW_STATIC_JOB')
  if ('provider.py' in r['cmd'] and 'gpu-' in r['cmd']):raise AssertionError('GPU_PROVIDER_OWNER')
  if 'supervisor' in r['cmd'] and r['pid']!=p['pid']:raise AssertionError('SUPERVISOR_CURRENT')
  if 'native-teacher-pipeline' in r['cmd']:assert set(r['affinity'])<={2,4,6},'176_CPU_POOL'
 other=sum(r['RSS'] for r in selected);assert other+2*1024**3+int(1.5*1024**3)<8*1024**3,'PARENT_RSS_HEADROOM'
 available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;assert available>int(2.25*1024**3),'PHYSICAL_RAM'
 q=subprocess.run(['nvidia-smi','--query-gpu=name,memory.free,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5);assert q.returncode==0 and int(q.stdout.split(',')[1].strip())*1024**2>=6*1024**3,'GPU_HEADROOM'
 g=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5);assert g.returncode==0 and not g.stdout.strip(),'GPU_COMPUTE_OWNER'
 control()
 bind=json.loads((D/'source-binding.json').read_text())
 for file,h in bind['hashes'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==h,'SOURCE_CHANGED'
 alloc=sum(f.stat().st_blocks*512 for b in [D,T] for f in b.rglob('*') if f.is_file());assert alloc+1048576<1835008 and 15069811+alloc+1048576<19922944,'STORAGE'
 return {'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scheduler_owned':None,'next_at':s['next_at'],'scheduler_identity':p,'critic_static_stop_sha':hashlib.sha256(stopfile.read_bytes()).hexdigest(),'critic_mock_pid_absent':cs['mock_PID'],'current_processes':selected,'other_RSS_B':other,'MemAvailable_B':available,'GPU_headroom':q.stdout.strip(),'GPU_compute_owners':g.stdout.strip(),'CPU_total_pool':[0,2,4,6],'RAM_forecast_contract_B':int(7.5*1024**3),'allocated_scope_B':alloc,'combined_plus_forecast_B':15069811+alloc+1048576}

rec={'receipt':json.loads((D/'intake.json').read_text())['receipt_UTC'],'manager':table()[SELF],'attempts':[],'science_jobs':0}
last=None
while not stop and time.time()<REG['newheavy_epoch']:
 try:a=admit();break
 except (AssertionError,OSError,ValueError,subprocess.TimeoutExpired) as e:
  reason=str(e)
  if reason!=last:rec['attempts'].append({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'defer':reason});last=reason;(D/'manager-current.json').write_text(json.dumps(rec,indent=2)+'\n');print('DEFERRED '+reason,flush=True)
  if reason in ('PAUSE','OWNER','SOURCE_CHANGED','DEADLINE'):stop=True
  if not stop:time.sleep(20)
else:
 rec.update(status='NN0_NO_WINDOW',owned_remaining=[]);(D/'manager-stop.json').write_text(json.dumps(rec,indent=2)+'\n');sys.exit(0)
(D/'admission.json').write_text(json.dumps(a,indent=2)+'\n')
start=time.time();env=os.environ.copy();env.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='0',CUDA_CACHE_DISABLE='1')
for n in ['tmp','xdg-cache','xdg-config']:(D/n).mkdir(exist_ok=True)
env.update(TMPDIR=str(D/'tmp'),XDG_CACHE_HOME=str(D/'xdg-cache'),XDG_CONFIG_HOME=str(D/'xdg-config'))
cmd=['taskset','-c','0','node',str(T/'measure.cjs')];log=(D/'run.stdout').open('w');err=(D/'run.stderr').open('w');child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=err,start_new_session=True);rec.update(science_jobs=1,start_epoch=start,command=cmd,child=table().get(child.pid));(D/'manager-current.json').write_text(json.dumps(rec,indent=2)+'\n');print('SCIENCE_STARTED '+str(child.pid),flush=True)
tracked={};peak=0;reason=None;lastcontrol=start;cpu_violation=False
while child.poll() is None:
 tab=table();members={child.pid}
 changed=True
 while changed:
  new={pid for pid,r in tab.items() if r['ppid'] in members or (r['ppid']==SELF and pid!=child.pid)};changed=not new.issubset(members);members|=new
 live=[tab[p] for p in members if p in tab];rss=sum(r['RSS'] for r in live)+tab.get(SELF,{}).get('RSS',0);peak=max(peak,rss)
 for r in live:tracked[(r['pid'],r['starttick'])]=r
 cpu_violation|=any(r['affinity']!=[0] for r in live)
 if stop:reason='MANAGER_STOP'
 elif time.time()-start>=180:reason='HARD180'
 elif rss>=REG['RAM_guard_B']:reason='RSS_GUARD'
 elif cpu_violation:reason='CPU_AFFINITY'
 elif time.time()>REG['processing_epoch']:reason='PROCESSING_DEADLINE'
 elif json.loads(S.read_text())['owned'] is not None:reason='SUPERVISOR_NEW_OWNED'
 elif sum(f.stat().st_blocks*512 for b in [D,T] for f in b.rglob('*') if f.is_file())>1835008:reason='STORAGE_GUARD'
 if time.time()-lastcontrol>=10:
  try:control()
  except Exception as e:reason=str(e)
  lastcontrol=time.time()
 if reason:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
  break
 time.sleep(.05)
child.wait(timeout=3);log.close();err.close()
# A stopped adopted child must be reaped; surviving exact tracked identities remain explicit.
for _ in range(100):
 try:pid,status=os.waitpid(-1,os.WNOHANG)
 except ChildProcessError:break
 if pid==0:break
nowtab=table();remaining=[r for (pid,tick),r in tracked.items() if pid in nowtab and nowtab[pid]['starttick']==tick];unknown=[r for r in nowtab.values() if r['ppid']==SELF]
rec.update(end_epoch=time.time(),elapsed_s=time.time()-start,exit=child.returncode,stop_reason=reason,peak_owned_RSS_B=peak,tracked=list(tracked.values()),owned_remaining=remaining,unknown_adopted=unknown,CPU_affinity_violation=cpu_violation,scientific_source_write_stopped=True)
(D/'manager-stop.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:rec[k] for k in ['elapsed_s','exit','stop_reason','peak_owned_RSS_B','owned_remaining','unknown_adopted']}),flush=True)
