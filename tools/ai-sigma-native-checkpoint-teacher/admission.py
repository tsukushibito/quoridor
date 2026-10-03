import os,json,time,datetime,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def allocated(paths):
 seen=set();n=0
 for base in paths:
  if not base.exists():continue
  for p in base.rglob('*'):
   if not p.is_file():continue
   s=p.stat();key=(s.st_dev,s.st_ino)
   if key not in seen:seen.add(key);n+=s.st_blocks*512
 return n
def admit(c,out,tool,runs):
 assert c['issue']=='quoridor-4lc.181' and c['mode']['cores'] in [[2],[2,4,6]]
 controls=[]
 for issue in ['quoridor-4lc','quoridor-4lc.181']:
  p=out/('admission-'+issue+'.json');assert time.time()-p.stat().st_mtime<60,'STALE_CONTROL';x=json.loads(p.read_text())[0];assert x['status']=='in_progress' and 'paused-by-user' not in x.get('labels',[]),'PAUSE_OR_STATUS'
  if issue.endswith('.180'):assert x['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746','OWNER'
  controls.append({k:x.get(k)for k in ['id','status','assignee','labels']})
 assert not (out/'PAUSE').exists()
 stop=json.loads((ROOT/'research-data/ai-sigma/176-native-teacher-pipeline/handoff-stop.json').read_text());assert stop['source_writer_stopped'] and stop['science_children_reaped'] and stop['backup_sync_exit']==0
 for p in (ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-TEACHER-PIPELINE/runs').glob('native176-*.process.json'):
  x=json.loads(p.read_text());assert not x['remaining'] and not x['unknown_adopted']
  for ident in x['tracked']:
   try:s=Path('/proc/'+str(ident['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(s[19])!=ident['start_ticks'],'OLD_CURRENT_IDENTITY'
 for p,h in json.loads((ROOT/'research-data/ai-sigma/181-checkpoint-teacher/binding.json').read_text())['readonly'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'BINDING_CHANGED'
 current=[];external=0
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:a=(p/'cmdline').read_bytes();s=(p/'stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if s[0]=='Z' or not (b'tools/ai-sigma-'in a or b'tools/research-team/'in a):continue
  own=b'ai-sigma-native-checkpoint-teacher'in a or b'native181-'in a
  affinity=sorted(os.sched_getaffinity(int(p.name)));rss=int(s[21])*4096
  if not own:
   assert set(affinity)<={0},'EXTERNAL_OWNER_ALLOCATION_UNKNOWN';external+=rss
   assert not any(w in a for w in [b'ort.py',b'provider.py',b'faithful-native',b'learn.py',b'engine.cjs',b'runner.py']),'EXTERNAL_HEAVY'
  current.append({'pid':int(p.name),'start_ticks':int(s[19]),'RSS':rss,'affinity':affinity,'own':own,'command':a.decode(errors='replace')[:180]})
 assert external+c['RAM']<=8*1024**3,'PARENT_RAM'
 assert int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024>c['RAM'],'HOST_RAM'
 own=allocated([tool,out,ROOT/'research-data/ai-sigma/181-checkpoint-teacher']);assert own+32*1024**2<224*1024**2,'SAVE_GUARD'
 old=allocated([ROOT/'tools'/n for n in ['ai-sigma-native-baseline','ai-sigma-native-runtime-ready','ai-sigma-native-ni-arena','ai-sigma-native-teacher-pipeline','ai-sigma-native-k800-time']]+[ROOT/'.artifacts/ai-sigma/resume-20261003'/n for n in ['NATIVE-BASELINE','NATIVE-RUNTIME-READY','NATIVE-NI-ARENA','NATIVE-TEACHER-PIPELINE','NATIVE-K800-TIME']]+[ROOT/'research-data/ai-sigma'/n for n in ['165-native-baseline','170-native-runtime-ready','173-native-ni-arena','176-native-teacher-pipeline','180-native-k800-time']]);assert old+256*1024**2<2044*1024**2,'RESERVATION_KNOWN'
 return {'decision':'launch_allowed','controls':controls,'current':current,'external_RSS':external,'scope_allocated':own,'known_old_allocated':old,'forecast':256*1024**2,'effective_experiment_reservation':2044*1024**2,'unknown_old_not_decremented':True,'host_load':Path('/proc/loadavg').read_text(),'CPU2_topology':{n:(Path('/sys/devices/system/cpu/cpu2/topology')/n).read_text()for n in ['core_id','physical_package_id','thread_siblings_list']},'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
