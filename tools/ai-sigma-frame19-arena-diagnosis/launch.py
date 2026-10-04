"""Short CPU0 NN0 child with fresh frame19 admission and exact PID/tick reaping."""
from pathlib import Path
import ctypes,datetime,hashlib,json,os,signal,subprocess,sys,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame19-arena-diagnosis';T=R/'tools/ai-sigma-frame19-arena-diagnosis'
os.sched_setaffinity(0,{4});ctypes.CDLL(None).prctl(36,1,0,0,0)
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
save=lambda p,j:p.write_text(json.dumps(j,indent=2)+'\n')
run=sys.argv[1];O=D/run;assert not O.exists();O.mkdir()
hard=30;deadline=datetime.datetime.fromisoformat('2026-10-04T23:45:00+00:00').timestamp()
def table():
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   a=(p/'stat').read_text().rsplit(')',1)[1].split();out[int(p.name)]={'pid':int(p.name),'ppid':int(a[1]),'tick':int(a[19]),'state':a[0],'RSS':int(a[21])*os.sysconf('SC_PAGE_SIZE')}
  except(OSError,ValueError):pass
 return out
anc={};tab=table();pid=tab[os.getpid()]['ppid']
while pid in tab and pid not in anc:anc[pid]=tab[pid]['tick'];pid=tab[pid]['ppid']
loaded_path=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame19/running-loaded.json'
sch_path=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json')
allowed={};permitted_CPU0=[]
def foreign(tab,owned={}):
 global permitted_CPU0
 rows=[]
 for pid,z in tab.items():
  if pid==os.getpid()or z['state']=='Z'or anc.get(pid)==z['tick']or allowed.get(pid)==z['tick']or owned.get(pid)==z['tick']:continue
  parent=z['ppid'];seen=set();own=False
  while parent in tab and parent not in seen:
   if parent==os.getpid()or owned.get(parent)==tab[parent]['tick']:own=True;break
   seen.add(parent);parent=tab[parent]['ppid']
  if own:continue
  try:argv=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
  except(OSError,UnicodeError):continue
  script=next((v for v in argv[1:6]if v.endswith(('.py','.js','.cjs'))and' 'not in v and Path(v).is_file()),'')
  if any(x in script for x in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/'])or (argv and'faithful-native'in argv[0]):rows.append({**z,'script':script,'argv':argv[:6],'affinity':sorted(os.sched_getaffinity(pid))})
 permitted_CPU0=[x for x in rows if 'frame19-native-independent' in x['script'] and x['affinity']==[0]]
 if sum(x['RSS'] for x in permitted_CPU0)>=448*1024**2:return rows
 return [x for x in rows if x not in permitted_CPU0]
try:
 assert time.time()+hard+5<deadline,'DEADLINE'
 for issue in ['quoridor-4lc','quoridor-4lc.239']:
  q=json.loads(subprocess.check_output(['bash','scripts/dev/beads.sh','show',issue,'--json'],timeout=10))[0]
  assert q['status']=='in_progress'and'paused-by-user'not in q.get('labels',[]),'PAUSE_OR_STATUS'
  if issue.endswith('.239'):assert q['assignee']=='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418','OWNER'
 loaded=json.loads(loaded_path.read_text());sch=json.loads(sch_path.read_text());tab=table()
 assert loaded['frame_start_fixed']=='2026-10-04T22:52:46Z','FRAME'
 assert loaded['deadlines']['final']=='2026-10-05T00:52:46Z','FRAME_END'
 assert loaded['parent_sha']==hashlib.sha256((R/'docs/design/ai-sigma-continuation-20261001.md').read_bytes()).hexdigest(),'PARENT_SHA'
 assert sch['phase']=='running'and not sch.get('recovery_required')and sch['owned']is None,'NATURAL_SUPERVISOR_OWNED'
 assert sch['next_at']-time.time()>hard+10,'QUIET_WINDOW'
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 for role in ['scheduler','monitor']:
  z=loaded[role].get('process',loaded[role]);assert tab.get(z['pid'],{}).get('tick')==int(z['start_ticks'])and z['boot_id']==boot,'RUNTIME_IDENTITY'
  allowed[z['pid']]=int(z['start_ticks'])
 mon=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mon.stat().st_mtime<120,'MONITOR_STALE'
 bind=json.loads((D/'preregister.json').read_text());assert os.sched_getaffinity(0)=={4},'AFFINITY';assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in bind['sources'].items()),'SOURCE_SHA'
 producer=json.loads((D/'producer-bindings.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in producer['paths_SHA'].items()),'PRODUCER_INPUT_SHA'
 stop=json.loads(Path(producer['producer_stop']).read_text());assert stop['science_stopped']and stop['children_waited_exactabsent'],'PRODUCER_STOP'
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for k in ['source_SHA','payload_SHA']for p,h in stop[k].items()),'PRODUCER_STOP_SHA'
 a=json.loads((R/'research-data/ai-sigma/frame19-native-arena/all-attempt-result-v1.json').read_text())
 for z in a['processes']:
  assert not z['remaining']and z['all_child_waited']and z['current_exact_absent'],'PRODUCER_CHILD_WAIT'
  for pid,tick in list(z['tracked'].items())+[(str(z['runner_pid']),z['runner_tick'])]:assert table().get(int(pid),{}).get('tick')!=int(tick),'PRODUCER_EXACT_IDENTITY'
 for bg in ['background-pilot-r2','background-later4-r1']:
  b=json.loads((R/'research-data/ai-sigma/frame19-native-arena'/bg/'result.json').read_text());assert b['cleanup_complete']and not b['remaining'],'BACKGROUND_CLEANUP'
 offenders=foreign(table());assert not offenders,('FOREIGN_COMPUTE',offenders)
 prior=[json.loads(p.read_text())for p in D.glob('*/process.json')];assert sum(z['science_charge_s'] for z in prior)+hard<=120,'SCIENCE_CAP'
 usage=sum(p.stat().st_size for base in[T,D]for p in base.rglob('*')if p.is_file());assert usage+720896<1572864,'STORAGE_FORECAST'
 parentRSS=sum(tab[p]['RSS']for p in anc if p in tab);runtimeRSS=sum(tab[p]['RSS']for p in allowed);assert parentRSS+runtimeRSS+sum(x['RSS']for x in permitted_CPU0)+512*1024**2<8*1024**3,'RAM_AGGREGATE'
 assert int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024>512*1024**2,'RAM_AVAILABLE'
 save(O/'admission.json',{'UTC':utc(),'frame19_loaded_path':str(loaded_path),'frame19_loaded_SHA':hashlib.sha256(loaded_path.read_bytes()).hexdigest(),'parent_SHA':loaded['parent_sha'],'runtime_PIDticks':allowed,'owned_control_ancestor_PIDticks':anc,'scheduler_owned':None,'next_supervisor_at':sch['next_at'],'quiet_s':sch['next_at']-time.time(),'current_foreign':offenders,'permitted_concurrent_CPU0_PIDticks_RSS':permitted_CPU0,'logical_compute_count':1+(1 if permitted_CPU0 else 0),'current_parent_RSS':parentRSS,'current_runtime_RSS':runtimeRSS,'storage_current_B':usage,'storage_forecast_extra_B':720896,'CPU':[4],'logical_scientific_CPUs':1,'RAM_guard_B':448*1024**2,'GPU_queries_allocation':0,'source_SHA':bind['sources'],'concurrent_CPU0_saved_arithmetic_allowed':True,'allhost_guarantee':False})
except Exception as e:
 save(O/'not-admitted.json',{'UTC':utc(),'typed':'NOT_ADMITTED','reason':str(e),'science_s':0,'NN':0});print(str(e));raise SystemExit(2)
tracked={};start=time.monotonic();startUTC=utc();peak=0;reason=None
cmd=['node',str(T/'diagnose.cjs'),str(D/'settings-r1.json')]
with(O/'stdout.txt').open('w')as log:
 child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);tracked[child.pid]=table()[child.pid]['tick']
 def group():
  tab=table();members={p for p,t in tracked.items()if tab.get(p,{}).get('tick')==t}|{p for p,z in tab.items()if z['ppid']==os.getpid()}
  while True:
   nxt={p for p,z in tab.items()if z['ppid']in members}
   if nxt<=members:break
   members|=nxt
  for p in members:
   if p in tab:tracked[p]=tab[p]['tick']
  return [tab[p]for p in members if p in tab]
 def kill(sig):
  for z in group():
   if z['state']!='Z':
    try:os.kill(z['pid'],sig)
    except ProcessLookupError:pass
 save(O/'actual-start.json',{'UTC':startUTC,'cmd':cmd,'runner_PID':os.getpid(),'runner_tick':table()[os.getpid()]['tick'],'child_PIDticks':tracked})
 while child.poll()is None:
  peak=max(peak,sum(z['RSS']for z in group())+table()[os.getpid()]['RSS'])
  if peak>=448*1024**2:reason='RAM_GUARD'
  if time.monotonic()-start>=hard or time.time()>=deadline:reason='TIME_GUARD'
  if foreign(table(),tracked):reason='FOREIGN_COMPUTE_STARTED'
  if json.loads(sch_path.read_text()).get('owned')is not None:reason='NATURAL_SUPERVISOR_STARTED'
  if (O/'PAUSE').exists():reason='PAUSE'
  if reason:kill(signal.SIGTERM);break
  time.sleep(.02)
 try:code=child.wait(timeout=2)
 except subprocess.TimeoutExpired:kill(signal.SIGKILL);code=child.wait(timeout=2)
 kill(signal.SIGKILL)
 for _ in range(100):
  try:
   pid,_=os.waitpid(-1,os.WNOHANG)
   if pid==0:time.sleep(.005)
  except ChildProcessError:break
 remaining=group();wall=time.monotonic()-start
 resultfile=Path(json.loads((D/'settings-r1.json').read_text())['output'])
 if code==0 and not reason:
  try:
   result=json.loads(resultfile.read_text());assert result['schema']=='frame19-arena-diagnosis-v1'and result['issue']=='quoridor-4lc.239'and result['task']=='saved-arena-ruleA-diagnosis';assert len(result['all8slots'])==8
  except Exception as e:reason='TASK_OR_SCHEMA_UNSETTLED:'+str(e)
 receipt={'UTC':utc(),'actual_start_UTC':startUTC,'exit':code,'reason':reason,'wall_s':wall,'science_charge_s':wall,'peak_family_RSS_B':peak,'tracked_PIDticks':tracked,'remaining':remaining,'all_waited':not remaining,'current_exact_absent':not remaining,'NN_model_torch_GPU':0,'runner_PID':os.getpid(),'runner_tick':table()[os.getpid()]['tick']}
 save(O/'process.json',receipt);print(json.dumps(receipt));raise SystemExit(0 if code==0 and not reason and not remaining else 1)
