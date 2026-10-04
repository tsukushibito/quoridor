"""226 owned NN0 job; physical admission, bounded wall, wait and point receipt."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time
D=Path('research-data/ai-sigma/frame18-worker-balance-independent');R=Path.cwd();os.sched_setaffinity(0,{0});utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,x): (D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table():
 out={}
 for p in Path('/proc').iterdir():
  if p.name.isdigit():
   try:
    z=(p/'stat').read_text().rsplit(')',1)[1].split();out[int(p.name)]={'PID':int(p.name),'PPID':int(z[1]),'tick':z[19],'state':z[0],'RSS':int(z[21])*4096}
   except (OSError,ValueError): pass
 return out
loadedpath=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame18/running-loaded.json'; loaded=json.loads(loadedpath.read_text());tab=table()
assert loaded['parent_sha']==hashlib.sha256((R/'docs/design/ai-sigma-continuation-20261001.md').read_bytes()).hexdigest(),'PARENT_BINDING'
for role in ['scheduler','monitor']:
 q=loaded[role].get('process',loaded[role]); assert str(tab[q['pid']]['tick'])==str(q['start_ticks']),'RUNTIME_IDENTITY'
monitor=Path(loaded['run'])/'monitor-observation.json';assert time.time()-monitor.stat().st_mtime<120,'STALE_MONITOR';mon=json.loads(monitor.read_text());schpath=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');sch=json.loads(schpath.read_text()); assert sch['phase']=='running' and not sch.get('recovery_required')
current=[];foreign=[]
for pid,z in tab.items():
 if pid==os.getpid() or z['state']=='Z':continue
 try: args=Path('/proc',str(pid),'cmdline').read_bytes().decode().split('\0');aff=sorted(os.sched_getaffinity(pid))
 except (OSError,UnicodeError):continue
 script=next((a for a in args[1:5] if a.endswith(('.py','.cjs','.js','.sh')) and ' ' not in a and '\n' not in a and Path(a).is_file()),'')
 research=any(k in script for k in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/','tools/research-team/','.artifacts/ai-sigma/continuation-20261001/'])
 if research:
  item={**z,'script':script,'affinity':aff};current.append(item)
  managed=script.endswith(('/save_git.py','/save.py','/pack.py','/scheduler.py','/monitor.py'))
  if not managed and ('tools/ai-sigma-' in script or 'tools/nnue-training/' in script or 'research-data/ai-sigma/' in script or (0 in aff and script.endswith('/guard.py'))): foreign.append(item)
assert not foreign,('CURRENT_PHYSICAL_FOREIGN',foreign)
gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,timeout=5,check=True).stdout.strip();assert not gpu,('GPU_CURRENT',gpu)
currentB=sum(p.stat().st_blocks*512 for p in D.iterdir() if p.is_file())+(R/'docs/reports/ai-sigma-critic-worker-balance.md').stat().st_blocks*512;forecast=currentB+262144+65536+131072;assert forecast<1048576
save('admission.json',{'UTC':utc(),'loaded':str(loadedpath),'monitor':str(monitor),'monitor_mtime':monitor.stat().st_mtime,'owned':sch.get('owned'),'next_at':sch.get('next_at'),'current':current,'GPU_current':gpu,'current_scope_allocated_B':currentB,'forecast_B':forecast,'reservation_B':2097152,'old_critic_B':117420516,'unknown_discount':0,'parent_added':0,'point_only':True})
start=utc(); t=time.monotonic();p=subprocess.Popen(['python3','-B',str(D/'check.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);tick=table()[p.pid]['tick'];reason=None
try: out,err=p.communicate(timeout=60)
except subprocess.TimeoutExpired:
 reason='OWN60_TIMEOUT';os.killpg(p.pid,signal.SIGTERM)
 try:out,err=p.communicate(timeout=3)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=3)
(D/'calc.log').write_bytes(out+err);now=table();exact=p.pid in now and now[p.pid]['tick']==tick
save('process.json',{'startUTC':start,'endUTC':utc(),'PID':p.pid,'tick':tick,'exit':p.returncode,'wait':True,'current_exact_absent':not exact,'jobwall_seconds':time.monotonic()-t,'stop_reason':reason,'CPU':[0],'newNN':0,'RAM_guard_B':469762048});print(json.dumps({'exit':p.returncode,'wall':time.monotonic()-t,'stdout':out.decode()[:2500],'stderr':err.decode()[:2500]}));assert p.returncode==0
