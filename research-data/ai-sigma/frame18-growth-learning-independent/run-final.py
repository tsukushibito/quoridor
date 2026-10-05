"""229 final bounded NN0 arithmetic; fresh frame18 physical admission."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time
os.sched_setaffinity(0,{0});D=Path('research-data/ai-sigma/frame18-growth-learning-independent');R=Path.cwd(); utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def table():
 o={}
 for p in Path('/proc').iterdir():
  if p.name.isdigit():
   try:s=(p/'stat').read_text().rsplit(')',1)[1].split();o[int(p.name)]={'PID':int(p.name),'PPID':int(s[1]),'tick':s[19],'state':s[0],'RSS':int(s[21])*4096,'CPUticks':int(s[11])+int(s[12])}
   except (OSError,ValueError):pass
 return o
def physics(exclude=()):
 current=[];foreign=[]
 for pid,z in table().items():
  if pid in (os.getpid(),*exclude) or z['state']=='Z':continue
  try:args=Path('/proc',str(pid),'cmdline').read_bytes().decode().split('\0');aff=sorted(os.sched_getaffinity(pid))
  except(OSError,UnicodeError):continue
  script=next((a for a in args[1:5]if a.endswith(('.py','.cjs','.js','.sh')) and ' 'not in a and '\n'not in a and Path(a).is_file()),'')
  if any(k in script for k in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/','tools/research-team/','.artifacts/ai-sigma/continuation-20261001/']):
   q={**z,'script':script,'affinity':aff};current.append(q)
   managed=script.endswith(('/save_git.py','/save.py','/pack.py','/scheduler.py','/watch.py'))
   if not managed and any(k in script for k in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/']):foreign.append(q)
 return current,foreign
P=R/'research-data/ai-sigma/frame18-data-learning'
binds={}
def bind(p,h=None):
 p=Path(p);v=hashlib.sha256(p.read_bytes()).hexdigest();assert h is None or v==h,(str(p),v,h);binds[str(p)]=v;return json.loads(p.read_text()) if p.suffix=='.json' else None
stop=bind(P/'scientific-final-stop.json','7cffd34e7aed02022bc7a321c87b26019d6f3d8ba38fc69c89ee2e2189d139a7');assert stop['science_sourcewriter_stopped'] and stop['children_waited'] and stop['current_exact_absent']
for root in ['source_SHA','payload_SHA']:
 for p,h in stop[root].items():bind(p,h)
tab=table()
for r in stop['learning_test_processes']:
 q=bind(r['path'],r['SHA']);assert q['exit']==0 and q['all_child_waited'] and q['current_exact_absent'] and not q['remaining']
 for pid,tick in {str(q['runner_pid']):q['runner_tick'],**q['tracked']}.items():assert int(pid) not in tab or str(tab[int(pid)]['tick'])!=str(tick)
for f in ['background-runtime-learn-r1/result.json','background-runtime-test-r1/result.json']:
 q=bind(P/f);assert q['cleanup_complete'] and q['outcome']=='succeeded' and q['exit_code']==0 and not q['remaining']
save('final-prestart-stop-binding.json',{'UTC':utc(),'inputSHA':binds,'both_background_cleanup_bound':True,'source_child_stop_bound':True,'earlier_data_gap_not_repaired':True})
loadedpath=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame18/running-loaded.json';loaded=json.loads(loadedpath.read_text());tab=table();assert loaded['parent_sha']==hashlib.sha256((R/'docs/design/ai-sigma-continuation-20261001.md').read_bytes()).hexdigest()
for role in ['scheduler','monitor']:
 p=loaded[role].get('process',loaded[role]);assert str(tab[p['pid']]['tick'])==str(p['start_ticks'])
mp=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mp.stat().st_mtime<120;sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert sch['phase']=='running'and not sch.get('recovery_required');current,foreign=physics();gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,timeout=5,check=True).stdout.strip();allocated=sum(p.stat().st_blocks*512 for p in D.iterdir()if p.is_file())+(R/'docs/reports/ai-sigma-critic-growth-learning.md').stat().st_blocks*512;forecast=allocated+1048576+524288+262144
admission={'UTC':utc(),'runtime':str(loadedpath),'monitor':str(mp),'monitor_mtime':mp.stat().st_mtime,'owned':sch.get('owned'),'next_at':sch.get('next_at'),'current':current,'foreign':foreign,'GPU':gpu,'scope_allocated':allocated,'scope_forecast':forecast,'new8MiBreservation':8388608,'old_unknown_discount':0,'parent_added':0,'point_not_allhost_future':True};save('final-admission.json',admission)
if foreign or gpu: save('final-not-started.json',{'UTC':utc(),'typed':'CURRENT_PHYSICAL_COMPETITION','newNN':0,'arithmetic_started':False});print(json.dumps({'NOT_STARTED':True,'foreign':foreign,'GPU':gpu}));raise SystemExit(0)
assert forecast<4194304;assert sum(p['RSS']for p in current)+512*1024**2<8*1024**3;assert int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))*1024>512*1024**2
start=utc();t=time.monotonic();p=subprocess.Popen(['python3','-B',str(D/'check-data.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);tick=table()[p.pid]['tick'];reason=None
while True:
 try:out,err=p.communicate(timeout=.1);break
 except subprocess.TimeoutExpired:
  _,foreign=physics((p.pid,));rss=table().get(p.pid,{}).get('RSS',0)
  if foreign or rss>=469762048 or time.monotonic()-t>=90:
   reason='FOREIGN_STARTED'if foreign else 'RAM_GUARD'if rss>=469762048 else '90SEC_GUARD';os.killpg(p.pid,signal.SIGTERM)
   try:out,err=p.communicate(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=3)
   break
(D/'final-calc.log').write_bytes(out+err);q=table().get(p.pid);receipt={'startUTC':start,'endUTC':utc(),'PID':p.pid,'tick':tick,'exit':p.returncode,'wait':True,'current_exact_absent':q is None or q['tick']!=tick,'wall':time.monotonic()-t,'reason':reason,'newNN':0,'CPU':[0],'cap90_no_reset':True};save('final-process.json',receipt);print(json.dumps({**receipt,'stdout':out.decode()[:2200],'stderr':err.decode()[:2200]}))
