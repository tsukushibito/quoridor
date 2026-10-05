import os,json,time,datetime,hashlib,importlib.util,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OLD=ROOT/'tools/ai-sigma-native-baseline';sp=importlib.util.spec_from_file_location('readonly165admission',OLD/'admission.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
ACTOR='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746'
def control(out,captured=False):
 rows=[]
 for id in ['quoridor-4lc','quoridor-4lc.173']:
  if captured:
   f=out/('admission-'+id+'.json');assert time.time()-f.stat().st_mtime<60,'CONTROL_READ_STALE';raw=f.read_bytes()
  else:raw=subprocess.check_output(['bash',str(ROOT/'scripts/dev/beads.sh'),'show',id,'--json'],timeout=8)
  x=json.loads(raw)[0];row={k:x.get(k) for k in ['id','status','labels','assignee','updated_at']};rows.append(row)
  assert row['status'] not in ['closed','blocked','deferred'] and 'paused-by-user' not in (row['labels'] or []),'PAUSE_OR_UNKNOWN'
  if id.endswith('.173'):assert row['assignee']==ACTOR,'OWNER'
 assert not (out/'PAUSE').exists(),'PAUSE'
 return rows

def physical(out,within=False):
 allrows={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:s=(p/'stat').read_text().rsplit(')',1)[1].split();a=(p/'cmdline').read_bytes()
  except (FileNotFoundError,ProcessLookupError):continue
  allrows[int(p.name)]={'pid':int(p.name),'ppid':int(s[1]),'start_ticks':int(s[19]),'RSS':int(s[21])*4096,'state':s[0],'args':a}
 current=[]
 for pid,x in allrows.items():
  args=x['args'];chain=x;seen=set();owned=False
  while chain and chain['pid'] not in seen:
   seen.add(chain['pid'])
   if b'ai-sigma-native-ni-arena' in chain['args'] or b'native173-' in chain['args']:owned=True;break
   chain=allrows.get(chain['ppid'])
  if x['state']=='Z':continue
  if b'/tools/ai-sigma-' in args or b'tools/ai-sigma-' in args or b'/tools/research-team/' in args or b'research-data/ai-sigma/' in args or owned:
   row={k:x[k]for k in ['pid','ppid','start_ticks','RSS']};row['affinity']=sorted(os.sched_getaffinity(pid));row['own']=owned;current.append(row)
   # The independently allocated CPU0 static/ops work stays outside the three arena cores.
   if not owned and (b'ai-sigma-' in args or b'research-data/ai-sigma/' in args) and not set(row['affinity'])<={0}:raise RuntimeError('EXTERNAL_COMPUTE_ALLOCATION_UNKNOWN')
 nonown=sum(x['RSS']for x in current if not x['own']);own=sum(x['RSS']for x in current if x['own']);assert nonown+(own if within else 4831838208)+134217728<8589934592,'PARENT_RAM'
 assert int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))*1024>(134217728 if within else 4831838208),'PHYSICAL_RAM'
 return current

def storage(out,tool):
 own=base.size([tool,out,ROOT/'research-data/ai-sigma/173-native-ni-arena']);paths=[]
 for t,a,d in [('ai-sigma-sigma-web-port','SIGMA-WEB-PORT','151-sigma-web-port'),('ai-sigma-native-baseline','NATIVE-BASELINE','165-native-baseline'),('ai-sigma-native-runtime-ready','NATIVE-RUNTIME-READY','170-native-runtime-ready'),('ai-sigma-cpu-concurrency','CPU-CONCURRENCY','159-cpu-concurrency'),('ai-sigma-fixed-cycle','FIXED-CYCLE','163-fixed-cycle'),('ai-sigma-nnue-feature-cost','NNUE-FEATURE-COST','156-nnue-feature-cost'),('ai-sigma-baseline-gap-frame10','BASELINE-GAP','frame10-baseline-gap')]:paths += [ROOT/'tools'/t,ROOT/'.artifacts/ai-sigma/resume-20261003'/a,ROOT/'research-data/ai-sigma'/d]
 old=base.size(paths);assert own+33554432<469762048 and old+536870912<2147483648,'STORAGE_FORECAST';return {'own_current_allocated':own,'old_retained_known_current':old,'new_reservation_in_existing_experiment':536870912,'guard':469762048,'Git_archive_index_remaining_forecast':33554432,'unknown_old_not_decremented':True,'parent_new_reservation':0}

def admit(c,out,tool,runs):
 assert c['issue']=='quoridor-4lc.173' and c['frame']==11;assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'DEADLINE'
 rows=control(out,captured=True);oldfiles=list((ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-RUNTIME-READY/runs').glob('*.process.json'))
 for p in oldfiles:
  x=json.loads(p.read_text());assert not x['remaining'] and not x['unknown_adopted'],'OLD_NOT_STOPPED'
  for i in x['tracked']+[{'pid':x['runner_pid'],'start_ticks':x['runner_starttick']}]:
   try:s=Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(s[19])!=i['start_ticks'],'OLD_CURRENT_IDENTITY'
 stop=ROOT/'research-data/ai-sigma/170-native-runtime-ready/science-stop.json';assert hashlib.sha256(stop.read_bytes()).hexdigest()=='b3e9abb87275a1c155b3f8f7efdb31c66972409dc3e92aebad5c507d4e8dde4e','OLD_STOP_BINDING'
 bind=json.loads((ROOT/'research-data/ai-sigma/173-native-ni-arena/binding.json').read_text());
 for f,h in bind['read_only_runtime'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,'READONLY_SOURCE_BINDING'
 assert hashlib.sha256((ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/build/target/release/faithful-native').read_bytes()).hexdigest()==bind['binary_SHA256'],'BINARY_BINDING'
 assert hashlib.sha256((ROOT/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx').read_bytes()).hexdigest()==bind['model_SHA256'],'MODEL_BINDING'
 pool=c['mode']['cores'];assert pool==[2,4,6] or c.get('mock') and pool==[2],'CPU_POOL'
 assert set(pool)<=os.sched_getaffinity(0) or os.sched_getaffinity(0)=={pool[0]},'CPUAFFINITY'
 cpuset=Path('/sys/fs/cgroup/cpuset.cpus.effective').read_text().strip();allowed=set()
 for p in cpuset.split(','):
  lo,hi=(map(int,p.split('-')) if '-' in p else (int(p),int(p)));allowed.update(range(lo,hi+1))
 assert set(pool)<=allowed,'CPUSET'
 topo=[{'CPU':i,'package':Path(f'/sys/devices/system/cpu/cpu{i}/topology/physical_package_id').read_text().strip(),'core':Path(f'/sys/devices/system/cpu/cpu{i}/topology/core_id').read_text().strip()}for i in pool];assert len({(x['package'],x['core'])for x in topo})==len(pool),'TOPOLOGY'
 current=physical(out);capacity=storage(out,tool)
 if not c.get('mock'):
  import tarfile
  archive=ROOT/'research-data/ai-sigma/174-gpu-inference/run-records.tar.gz'
  with tarfile.open(archive)as t:
   stopname=next(n for n in t.getnames()if n.endswith('manager-stop.json'));gpu=json.load(t.extractfile(stopname))
  assert not gpu['owned_wait_remaining'] and not gpu['current_child_exact_identity_present'],'GPU_NOT_STOPPED'
  for i in [gpu['child_identity'],{'pid':gpu['manager_pid'],'starttick':gpu['manager_starttick']}]:
   try:st=Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert st[19]!=str(i['starttick']),'GPU_CURRENT_IDENTITY'
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:a=(p/'cmdline').read_bytes();st=(p/'stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   if st[0]!='Z' and b'ai-sigma-gpu-inference/measure.py' in a:raise RuntimeError('GPU_FORWARD_ACTIVE')
  (out/'gpu-nonoverlap-admission.json').write_text(json.dumps({'archive_SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'child':gpu['child_identity'],'current_identity':False,'new_forward_process_observed':False,'allhost_guarantee':False},indent=2)+'\n')

 for f in runs.glob('native173-*.process.json'):
  z=json.loads(f.read_text());assert not z['remaining'] and not z['unknown_adopted'],'OWN_PREVIOUS_REMAINS'
  if not c.get('mock') and z['phase']=='quality' and not (c.get('epoch')==2 and z['name']=='native173-quality-r1'):raise RuntimeError('SCIENTIFIC_ATTEMPT_ALREADY_REGISTERED_NO_REPLACEMENT')
 if not c.get('mock'):
  p=json.loads((ROOT/'research-data/ai-sigma/173-native-ni-arena/preregister-e2.json').read_text());assert p['science_ready'] and p['statistics']['status']=='ADOPTED','PREREG_MISSING'
 return{'decision':'launch_allowed','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'control':rows,'research_current':current,'storage':capacity,'CPU_topology':topo,'LLMactive_gate':False,'CPU0_reserved_ops':True,'physical_wholeperiod_guarantee':False}
