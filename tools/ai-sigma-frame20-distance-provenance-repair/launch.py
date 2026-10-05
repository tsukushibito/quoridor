"""One NN0 CPU4 job, fresh positive frame20/runtime binding and exact reap."""
from pathlib import Path
import ctypes,datetime,gzip,hashlib,json,os,signal,subprocess,sys,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame20-distance-provenance-repair'
os.sched_setaffinity(0,{4});ctypes.CDLL(None).prctl(36,1,0,0,0)
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def table():
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   a=(p/'stat').read_text().rsplit(')',1)[1].split();out[int(p.name)]={'pid':int(p.name),'ppid':int(a[1]),'tick':int(a[19]),'state':a[0],'RSS':int(a[21])*os.sysconf('SC_PAGE_SIZE')}
  except(OSError,ValueError):pass
 return out
tab=table();anc={};p=tab[os.getpid()]['ppid']
while p in tab and p not in anc:anc[p]=tab[p]['tick'];p=tab[p]['ppid']
allowed={};loadedpath=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/ROLE-MILESTONE-247/running-loaded.json'
schpath=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json')
def foreign(owned={}):
 rows=[];tab=table()
 for p,z in tab.items():
  if p==os.getpid()or z['state']=='Z'or anc.get(p)==z['tick']or allowed.get(p)==z['tick']or owned.get(p)==z['tick']:continue
  parent=z['ppid'];seen=set();own=False
  while parent in tab and parent not in seen:
   if parent==os.getpid()or owned.get(parent)==tab[parent]['tick']:own=True;break
   seen.add(parent);parent=tab[parent]['ppid']
  if own:continue
  try:argv=Path(f'/proc/{p}/cmdline').read_bytes().decode().split('\0')
  except(OSError,UnicodeError):continue
  script=next((x for x in argv[1:7]if x.endswith(('.py','.js','.cjs'))and' 'not in x and Path(x).is_file()),'')
  if any(x in script for x in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/'])or(argv and'faithful-native'in argv[0]):rows.append({**z,'script':script,'affinity':sorted(os.sched_getaffinity(p))})
 return rows
hard=90;newdeadline=datetime.datetime.fromisoformat('2026-10-05T01:45:00+00:00').timestamp();stopdeadline=datetime.datetime.fromisoformat('2026-10-05T01:48:00+00:00').timestamp()
c=json.loads((D/'settings.json').read_text());reg=json.loads((D/'preregister.json').read_text())
O=D/'single-job';O.mkdir(exist_ok=True)
try:
 assert not(D/'actual-start.json').exists(),'MAX1_ALREADY_STARTED'
 assert time.time()<newdeadline and time.time()+hard+30<stopdeadline,'DEADLINE'
 for issue in ['quoridor-4lc','quoridor-4lc.248']:
  j=json.loads(subprocess.check_output(['bash','scripts/dev/beads.sh','show',issue,'--json'],timeout=10))[0];assert j['status']=='in_progress'and'paused-by-user'not in j.get('labels',[]),'PAUSE_STATUS'
  if issue.endswith('.248'):assert j['assignee']=='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418','OWNER'
 loaded=json.loads(loadedpath.read_text());sch=json.loads(schpath.read_text());cfg=loaded['config'];boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();tab=table()
 assert cfg['start_at']=='2026-10-05T00:51:02Z'and cfg['end_at']=='2026-10-05T02:46:02Z','FRAME20'
 assert sch['phase']=='running'and not sch.get('recovery_required')and sch['owned']is None,'NATURAL_OWNED'
 assert sch['next_at']-time.time()>hard+30,'NATURAL_QUIET_WINDOW'
 for role in ['scheduler','monitor']:
  z=loaded[role].get('process',loaded[role]);assert tab.get(z['pid'],{}).get('tick')==int(z['start_ticks'])and z['boot_id']==boot,'RUNTIME_IDENTITY';allowed[z['pid']]=int(z['start_ticks'])
 assert sha(sch['config_path'])==sch['config_sha256']==loaded['state']['config_sha256'],'CONFIG_BIND'
 assert sha(sch['binding']['contract_file'])==sch['contract_sha256']==loaded['state']['contract_sha256'],'CONTRACT_BIND'
 parent=R/'docs/design/ai-sigma-continuation-20261001.md';assert sha(parent)==loaded['monitor']['expected_input_hashes'][str(parent)],'PARENT_BIND'
 assert len(loaded['monitor']['expected_input_hashes'])==24 and all(sha(p)==h for p,h in loaded['monitor']['expected_input_hashes'].items()),'CURRENT_LOADED24HASH'
 assert loaded['input_mismatches']==[] and loaded['input_count']==24 and loaded['six_digests_match'],'CURRENT_ROLE247_BIND'
 mon=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mon.stat().st_mtime<120,'MONITOR_FRESH'
 assert os.sched_getaffinity(0)=={4};assert all(sha(p)==h for p,h in reg['sources'].items()),'SOURCE_INPUT_BIND'
 assert all(sha(p)==h for key in ['producer_source9_current_SHA','producer_payload7_current_SHA'] for p,h in reg[key].items()),'PRODUCER_CURRENT_SOURCE_PAYLOAD'
 stop=json.loads(Path(reg['producer_stop']).read_text());assert stop['scientific_source_writer_stopped']and stop['all_child_waited']and stop['current_exact_absent'],'PRODUCER_STOP'
 for z in stop['all_attempt_processes']:
  assert z['all_child_waited']and z['current_exact_absent']and not z['remaining']
  for p,t in list(z['tracked'].items())+[(z['runner_pid'],z['runner_tick'])]:assert table().get(int(p),{}).get('tick')!=int(t),'PRODUCER_IDENTITY'
 for p in reg['producer_background_results']:
  j=json.loads(Path(p).read_text());assert j['cleanup_complete']and not j['remaining'],'PRODUCER_BACKGROUND_CLEANUP'
 newstop=json.loads(Path(reg['producer_newstop']).read_text());assert newstop['new_phase_source_stopped'] and newstop['waited_exactabsence'],'NEWPRODUCER_STOP'
 proc=json.loads(Path(reg['producer_newprocess']).read_text());assert proc['waited'] and proc['current_exact_absent'],'NEWPRODUCER_WAIT'
 assert table().get(proc['pid'],{}).get('tick')!=int(proc['tick']),'NEWPRODUCER_EXACT'
 for path in reg['additional_stopped_processes']:
  proc=json.loads(Path(path).read_text());assert proc.get('wait',proc.get('all_child_waited',False)) and proc['current_exact_absent'],'OTHER_WAIT'
  if 'PID' in proc:assert table().get(proc['PID'],{}).get('tick')!=int(proc['tick']),'OTHER_EXACT'
  else:
   for pid,tick in list(proc['tracked_PIDticks'].items())+[(proc['runner_PID'],proc['runner_tick'])]:assert table().get(int(pid),{}).get('tick')!=int(tick),'OLD244_EXACT'
 offenders=foreign();assert not offenders,('FOREIGN_COMPUTE',offenders)
 forecast=json.loads((D/'storage-forecast.json').read_text());assert forecast['forecast_B']<=524288 and forecast['guard_B']==786432,'STORAGE'
 parentRSS=sum(tab[p]['RSS']for p in anc if p in tab);runtimeRSS=sum(tab[p]['RSS']for p in allowed);assert parentRSS+runtimeRSS+512*1024**2<8*1024**3,'AGGREGATE_RAM'
 assert int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024>512*1024**2,'RAM_AVAILABLE'
 save(D/'admission.json',{'UTC':utc(),'frame20_loaded_path':str(loadedpath),'frame20_loaded_SHA':sha(loadedpath),'runtime_PIDticks':allowed,'management_ancestor_PIDticks':anc,'parent_SHA':sha(parent),'config_SHA':sch['config_sha256'],'contract_SHA':sch['contract_sha256'],'owned':None,'next_supervisor_at':sch['next_at'],'quiet_s':sch['next_at']-time.time(),'CPU':[4],'logical_scientific_CPU':1,'current_foreign':offenders,'parentRSS':parentRSS,'runtimeRSS':runtimeRSS,'family_guard_B':448*1024**2,'forecast_B':forecast['forecast_B'],'GPU_query_allocation':0,'source_inputs_PASS':True,'producer_current_absent_cleanup_PASS':True,'allhost_future_guarantee':False})
except Exception as e:
 save(D/'not-admitted.json',{'UTC':utc(),'typed':'NOT_ADMITTED','reason':str(e),'scientific_job_started':False,'NN':0});print(str(e));sys.exit(2)
cmd=c['argv'];tracked={};reason=None;peak=0;start=time.monotonic()
with(O/'stdout.txt').open('w')as log:
 child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 tracked[child.pid]=table()[child.pid]['tick']
 save(D/'actual-start.json',{'UTC':utc(),'argv':cmd,'task':c['task'],'schema':c['schema'],'runner_PID':os.getpid(),'runner_tick':table()[os.getpid()]['tick'],'child_PIDticks':tracked,'CPU':[4],'MAX1_started':True})
 def group():
  tab=table();ids={p for p,t in tracked.items()if tab.get(p,{}).get('tick')==t}|{p for p,z in tab.items()if z['ppid']==os.getpid()}
  while True:
   nxt={p for p,z in tab.items()if z['ppid']in ids}
   if nxt<=ids:break
   ids|=nxt
  for p in ids:
   if p in tab:tracked[p]=tab[p]['tick']
  return[tab[p]for p in ids if p in tab]
 def kill(sig):
  for z in group():
   if z['state']!='Z':
    try:os.kill(z['pid'],sig)
    except ProcessLookupError:pass
 while child.poll()is None:
  peak=max(peak,sum(z['RSS']for z in group())+table()[os.getpid()]['RSS'])
  if peak>=448*1024**2:reason='FAMILY_RAM_GUARD'
  if time.monotonic()-start>=hard or time.time()>=stopdeadline:reason='TIME_GUARD'
  if foreign(tracked):reason='FOREIGN_COMPUTE_STARTED'
  if json.loads(schpath.read_text()).get('owned')is not None:reason='SUPERVISOR_STARTED'
  if(D/'PAUSE').exists():reason='PAUSE'
  if reason:kill(signal.SIGTERM);break
  time.sleep(.02)
 try:code=child.wait(timeout=3)
 except subprocess.TimeoutExpired:kill(signal.SIGKILL);code=child.wait(timeout=3)
 kill(signal.SIGKILL)
 for _ in range(100):
  try:
   pid,_=os.waitpid(-1,os.WNOHANG)
   if pid==0:time.sleep(.01)
  except ChildProcessError:break
 remaining=group();wall=time.monotonic()-start;purpose=None
 if code==0 and not reason:
  try:
   j=json.loads(gzip.decompress(Path(c['output']).read_bytes()));assert j['task']==c['task']and j['schema']==c['schema']and j['issue']=='quoridor-4lc.248';assert j['status']=='COMPLETED'and j['planned']==16 and len(j['conditions'])==16;assert j['NN']==0 and j['processed']<=65536;assert all(x['status']=='COMPLETED'for x in j['conditions']);purpose=True
   assert Path(c['output']).stat().st_size<=98304,'OUTPUT_SIZE_GUARD'
  except Exception as e:reason='TASK_SCHEMA_UNSETTLED:'+str(e)
 save(D/'process.json',{'UTC':utc(),'exit':code,'reason':reason,'purpose_identity_PASS':purpose,'wall_s':wall,'science_charge_s':wall,'peak_family_RSS_B':peak,'tracked_PIDticks':tracked,'remaining':remaining,'all_child_waited':not remaining,'current_exact_absent':not remaining,'runner_PID':os.getpid(),'runner_tick':table()[os.getpid()]['tick'],'NN_GPU':0,'CPU':[4]})
 print(json.dumps({'exit':code,'reason':reason,'wall_s':wall,'peak_family_RSS_B':peak,'current_exact_absent':not remaining}));sys.exit(0 if code==0 and not reason and not remaining else 1)
