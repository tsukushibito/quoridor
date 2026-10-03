import os,json,time,datetime,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ACTOR='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746'
def allocated(paths):
 seen=set();total=0
 for base in paths:
  for p in base.rglob('*') if base.exists() else []:
   if not p.is_file():continue
   x=p.stat();key=(x.st_dev,x.st_ino)
   if key not in seen:seen.add(key);total+=x.st_blocks*512
 return total
def admit(c,out,tool,runs):
 assert c['issue']=='quoridor-4lc.176' and c['frame']==12
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp()
 control=[]
 for id in ['quoridor-4lc','quoridor-4lc.176']:
  p=out/('admission-'+id+'.json');assert time.time()-p.stat().st_mtime<60,'CONTROL_STALE';x=json.loads(p.read_text())[0]
  assert x['status']=='in_progress' and 'paused-by-user' not in (x.get('labels') or []),'PAUSED_OR_UNKNOWN'
  if id.endswith('.176'):assert x['assignee']==ACTOR,'OWNER_UNKNOWN'
  control.append(x)
 assert not (out/'PAUSE').exists(),'PAUSED'
 bind=json.loads((ROOT/'research-data/ai-sigma/176-native-teacher-pipeline/binding.json').read_text())
 for p,h in bind['reused_source'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'SOURCE_BINDING'
 model=ROOT/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';assert hashlib.sha256(model.read_bytes()).hexdigest()==bind['model_SHA256'],'MODEL_BINDING'
 for p in (ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-NI-ARENA/runs').glob('*.process.json'):
  x=json.loads(p.read_text());assert not x['remaining'] and not x['unknown_adopted'],'OLD_NOT_STOPPED'
  for i in x['tracked']:
   try:s=Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(s[19])!=i['start_ticks'],'OLD_CURRENT_IDENTITY'
 pool=c['mode']['cores'];assert pool in [[2],[2,4],[2,4,6]] or (c.get('efficiency_adoption') and pool==[0,2,4,6])
 gpu_admission=None
 if c.get('efficiency_adoption'):
  if c.get('backend') in ['cpuort','cuda']:
   release=json.loads((ROOT/'research-data/ai-sigma/179-native-teacher-independent/science-stop.json').read_text());assert release['NN_executed']==0,'179_RELEASE_UNKNOWN'
   for ident in release['CPU0_science_children']:assert not Path('/proc/'+str(ident['PID'])).exists(),'179_SCIENCE_CURRENT'
  scheduler=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert scheduler['phase']=='running' and not scheduler['recovery_required'] and scheduler['owned'] is None,'SUPERVISOR_NOT_QUIET'
  assert scheduler['next_at']-time.time()>c['job_seconds']+30,'SUPERVISOR_QUIET_WINDOW'
  ident=scheduler['process'];sp=Path('/proc/'+str(ident['pid'])+'/stat').read_text().rsplit(')',1)[1].split();assert int(sp[19])==int(ident['start_ticks']),'SUPERVISOR_IDENTITY'
  assert hashlib.sha256(Path(scheduler['config_path']).read_bytes()).hexdigest()==scheduler['config_sha256'],'SUPERVISOR_BINDING'
  stop=json.loads((ROOT/'research-data/ai-sigma/177-gpu-batch-provider/manager-stop.json').read_text());assert stop['scientific_source_write_stopped'] and not stop['owned_remaining'] and not stop['unknown_adopted'],'177_STOP'
  for ident in [stop['manager'],*stop['tracked']]:
   try:st=Path('/proc/'+str(ident['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(st[19])!=int(ident['starttick']),'177_CURRENT_IDENTITY'
  for p,h in json.loads((ROOT/'research-data/ai-sigma/176-native-teacher-pipeline/gpu-source-binding.json').read_text())['readonly_source'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'177_SOURCE_BINDING'
  if c.get('backend')=='cuda' or c.get('gpu_parity'):
   capture=out/'gpu-physical-current.json';assert time.time()-capture.stat().st_mtime<60,'GPU_PHYSICAL_STALE';gpu_admission=json.loads(capture.read_text());assert gpu_admission['query_exit']==0 and gpu_admission['owners_query_exit']==0 and not gpu_admission['compute_owners'].strip(),'GPU_OWNER'
   assert int(gpu_admission['headroom'].split(',')[1].strip())*1024**2>=6*1024**3,'GPU_HEADROOM'
 for core in pool:assert Path(f'/sys/devices/system/cpu/cpu{core}').exists(),'CORE_UNAVAILABLE'
 current=[];external=0
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:a=(p/'cmdline').read_bytes();s=(p/'stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if s[0]=='Z':continue
  if b'tools/ai-sigma-' not in a and b'tools/research-team/' not in a:continue
  own=b'ai-sigma-native-teacher-pipeline' in a or b'native176-' in a
  affinity=sorted(os.sched_getaffinity(int(p.name)));rss=int(s[21])*4096
  if not own:
   assert set(affinity)<={0},'EXTERNAL_COMPUTE_ALLOCATION_UNKNOWN';external+=rss
  current.append({'PID':int(p.name),'start_ticks':int(s[19]),'RSS':rss,'affinity':affinity,'own':own})
 # Allocated concurrent roles: exp4+hyp2+critic.5+super1+stew.5=8GiB.
 assert external+c.get('RAM',4294967296)<=8589934592,'PARENT_RAM_HEADROOM'
 assert int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024>c.get('RAM',4294967296),'PHYSICAL_RAM'
 own=allocated([tool,out,ROOT/'research-data/ai-sigma/176-native-teacher-pipeline'])
 assert own+33554432<234881024,'SAVE_GUARD_FORECAST'
 old=allocated([ROOT/'tools'/n for n in ['ai-sigma-native-baseline','ai-sigma-native-runtime-ready','ai-sigma-native-ni-arena']]+[ROOT/'.artifacts/ai-sigma/resume-20261003'/n for n in ['NATIVE-BASELINE','NATIVE-RUNTIME-READY','NATIVE-NI-ARENA']]+[ROOT/'research-data/ai-sigma'/n for n in ['165-native-baseline','170-native-runtime-ready','173-native-ni-arena']])
 assert old+268435456<2044*1024*1024,'EXPERIMENT_RESERVATION'
 for p in runs.glob('native176-*.process.json'):
  x=json.loads(p.read_text());assert not x['remaining'] and not x['unknown_adopted'],'OWN_NOT_COLLECTED'
 return {'decision':'launch_allowed','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'control':control,'current':current,'external_RSS':external,'own_allocated':own,'old_known_retained_allocated':old,'old_unknown_not_decremented':True,'experiment_effective_reservation':2044*1024*1024,'new_scope_reservation':268435456,'new_parent_reservation':0,'LLMactive_gate':False,'GPU_physical':gpu_admission,'efficiency_supervisor_quiet':bool(c.get('efficiency_adoption'))}
