import os,json,time,datetime,hashlib,importlib.util
from pathlib import Path
OLD=Path(__file__).resolve().parent.parent/'ai-sigma-native-baseline';sp=importlib.util.spec_from_file_location('readonlyAdmission165',OLD/'admission.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def decide(a):return isinstance(a,dict) and a.get('decision')=='launch_allowed'
def admit(c,out,tool,runs):
 root=tool.parents[1];assert c['issue']=='quoridor-4lc.170' and c['frame']==11
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'DEADLINE'
 for id in ['quoridor-4lc','quoridor-4lc.170']:
  p=out/('admission-'+id+'.json');assert time.time()-p.stat().st_mtime<60,'CONTROL_READ_STALE';z=json.loads(p.read_text())[0];assert z['status'] not in ['closed','blocked','deferred'] and 'paused-by-user' not in z.get('labels',[]),'PAUSE'
  if id.endswith('.170'):assert z.get('assignee')=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746','OWNER'
 assert not (out/'PAUSE').exists(),'PAUSE'
 stop=root/'research-data/ai-sigma/165-native-baseline/control-repair-stop.json';assert hashlib.sha256(stop.read_bytes()).hexdigest()=='b5d9b87d15cd93c4da198a3ee518c41de727acc867806857c653549160efb7c8';z=json.loads(stop.read_text())
 for p,h in z['source_hashes'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,'ORIGINAL_SOURCE_CHANGED'
 prior=[json.loads(p.read_text()) for p in (root/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/runs').glob('native165-*.process.json')];new=[json.loads(p.read_text()) for p in runs.glob('native170-*.process.json')]
 for x in prior+new:
  assert not x['remaining'] and not x['unknown_adopted'],'OWNED_REMAINS'
  for i in x['tracked']+[{'pid':x['runner_pid'],'start_ticks':x['runner_starttick']}]:
   try:s=Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(s[19])!=i['start_ticks'],'OLD_CURRENT_IDENTITY'
 heavy,meta=base.base.physical_heavy_scan();assert base.base.base.decide(heavy,prior+new) is True,'EXTERNAL_HEAVY_UNKNOWN'
 pool=c['mode']['cores'];assert len(pool)==len(set(pool)) and pool==([2,4,6,8] if c['kind']=='parallel' else [2]);allowed=set();cpuset=Path('/sys/fs/cgroup/cpuset.cpus.effective').read_text().strip();
 for part in cpuset.split(','):
  lo,hi=(map(int,part.split('-')) if '-' in part else (int(part),int(part)));allowed.update(range(lo,hi+1))
 assert set(pool)<=allowed,'CPUSET'
 research=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try:s=(p/'stat').read_text().rsplit(')',1)[1].split();args=(p/'cmdline').read_bytes()
  except (FileNotFoundError,ProcessLookupError):continue
  if s[0]!='Z' and (b'/tools/ai-sigma-' in args or b'/tools/research-team/' in args):
   row={'pid':int(p.name),'start_ticks':int(s[19]),'RSS':int(s[21])*4096,'affinity':sorted(os.sched_getaffinity(int(p.name)))};research.append(row)
   if c['kind']=='parallel' and (args.startswith((b'python',b'/usr/bin/python',b'node',b'/usr/bin/node',b'/home/vscode/.cache/inference/'))) and any(a not in pool for a in row['affinity']):raise RuntimeError('EXTERNAL_STATIC_OR_POOL_CONFLICT')
 scheduler=None
 if c['kind']=='parallel':
  assert (out/'runs/native170-solo-r1/result.json').exists(),'SOLO_MISSING';solo=json.loads((out/'runs/native170-solo-r1/result.json').read_text());assert solo['basic_runtime_supported'],'SOLO_UNSUPPORTED'
  path=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');s=json.loads(path.read_text());p=s.get('process');assert s['phase']=='running' and not s.get('recovery_required') and p and isinstance(s.get('next_at'),(int,float)),'SCHEDULER_UNKNOWN';st=Path('/proc/'+str(p['pid'])+'/stat').read_text().rsplit(')',1)[1].split();assert st[19]==str(p['start_ticks']),'SCHEDULER_IDENTITY';assert s['next_at']>time.time()+65,'NEXT_OBSERVE_OVERLAP';scheduler={'SHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'next_at':s['next_at'],'process':p,'owned_turn_observed':s.get('owned'),'no_LLMACTIVE_gate':True};
  topo=[{'CPU':i,'package':Path(f'/sys/devices/system/cpu/cpu{i}/topology/physical_package_id').read_text().strip(),'core':Path(f'/sys/devices/system/cpu/cpu{i}/topology/core_id').read_text().strip()} for i in pool];assert len({(t['package'],t['core']) for t in topo})==4,'SAME_PHYSICAL_CORE'
 else:topo=[]
 required=6979321856 if c['kind']=='parallel' else 2147483648;mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;assert mem>required,'PHYSICAL_RAM';assert sum(x['RSS'] for x in research)+required+134217728<8589934592,'PARENT_RAM'
 own=base.size([tool,out,root/'research-data/ai-sigma/170-native-runtime-ready']);old=base.size([root/'tools/ai-sigma-native-baseline',root/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE',root/'research-data/ai-sigma/165-native-baseline',root/'tools/ai-sigma-sigma-web-port',root/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT',root/'research-data/ai-sigma/151-sigma-web-port',root/'tools/ai-sigma-baseline-gap-frame10',root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP',root/'research-data/ai-sigma/frame10-baseline-gap',root/'tools/ai-sigma-nnue-feature-cost',root/'.artifacts/ai-sigma/resume-20261003/NNUE-FEATURE-COST',root/'research-data/ai-sigma/156-nnue-feature-cost']);assert own+c['forecast_bytes']<7340032 and old+own+c['forecast_bytes']<2147483648,'STORAGE'
 seconds=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in new if x['phase'] in ['solo','parallel']);assert seconds<120,'HEAVY_BUDGET'
 for x in new:
  if x['phase']==c['kind'] and x['phase']!='mock':raise RuntimeError('SUCCESS_OR_ATTEMPT_ALREADY_REGISTERED_NO_REPLACEMENT')
 return {'decision':'launch_allowed','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_child_spawn':True,'research_current':research,'external_heavy':heavy,'external_metadata':meta,'scheduler':scheduler,'CPU_topology':topo,'own_current':own,'own_forecast':c['forecast_bytes'],'guard':7340032,'old_retained_current':old,'old_unknown_not_decremented':True,'parent_RAM':8589934592,'job_RAM':required,'RAM_available':mem,'parent_additional_reservation':0,'used_heavy_s':seconds,'current_identity_absent_is_not_allperiod_or_allhost_guarantee':True}
