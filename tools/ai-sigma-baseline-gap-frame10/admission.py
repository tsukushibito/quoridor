"""One fail-closed admission branch, before sole child spawn. Read-only external identities."""
import json,os,time,datetime,hashlib,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'ai-sigma-local-move-quality/admission.py'
sp=importlib.util.spec_from_file_location('readonlyPhysical134',p);base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def admit(c,out,tool,runs):
 previous=[json.loads(p.read_text()) for p in runs.glob('gap149-*.process.json')]
 assert base.base.decide([],previous) is True,'OLD_OWNED_NOT_ZERO'
 heavy,metadata=base.physical_heavy_scan() if c['kind']=='ai' else ([],[])
 assert base.base.decide(heavy,previous) is True,'EXTERNAL_HEAVY_UNKNOWN'
 same=[]
 stop_path=tool.parents[1]/'research-data/ai-sigma/144-wallless-ai-sensitivity/final-source-stop.json'
 science_path=stop_path.with_name('runtime-source-stopped-before-report.json')
 assert hashlib.sha256(stop_path.read_bytes()).hexdigest()=='223a4866d89cf68695503077111537bdd889a6db0af4691cde5b02f60bf938be','OLD144_FINAL_STOP_SHA'
 assert hashlib.sha256(science_path.read_bytes()).hexdigest()=='7bc78b82079538b71d7263270154171f371f187b314128ae6a517964376d42da','OLD144_SCIENCE_STOP_SHA'
 stop=json.loads(stop_path.read_text());science=json.loads(science_path.read_text())
 assert stop['scientific_source_stop_before_body'] and stop['verification_source_write_stopped'] and stop['outer_ownedwait_remainingunknown0'],'OLD144_NOT_STOPPED'
 assert science['all_searches_zero'] and science['outer_ownedwait_remainingunknown0'],'OLD144_SEARCH_UNKNOWN'
 assert stop['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'BOOT_CHANGED'
 for x in stop['identities']:
  try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==x['start_ticks']:same.append(x)
 assert not same,'OLD144_CURRENT_IDENTITY'
 mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','MemFree:'))}
 assert mem['MemAvailable']>=(1073741824 if c['kind']=='protocol' else 6442450944),'PHYSICAL_RAM_HEADROOM'
 # Read current RSS of identifiable research runtime/static jobs. Reservations use actual current,
 # not past peaks. LLM/App Server processes are operational, not extra Chrome grants.
 current_research=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try:
   s=(p/'stat').read_text().rsplit(')',1)[1].split();a=(p/'cmdline').read_bytes().split(b'\0');argv=[v.decode() for v in a if v]
   if s[0]=='Z':continue
   if any('/tools/ai-sigma-' in v or '/tools/research-team/' in v for v in argv):
    current_research.append({'pid':int(p.name),'start_ticks':int(s[19]),'rss':int(s[21])*4096,'argv_SHA256':hashlib.sha256(json.dumps(argv).encode()).hexdigest()})
  except (FileNotFoundError,ProcessLookupError):continue
 # 128MiB explicitly conservative operation headroom, actual static current kept separate.
 research_current=sum(x['rss'] for x in current_research)
 assert research_current+(1073741824 if c['kind']=='protocol' else 6442450944)+134217728<8589934592,'PARENT8_CURRENT_HEADROOM'
 used=sum((datetime.datetime.fromisoformat(d['end'])-datetime.datetime.fromisoformat(d['start'])).total_seconds() for d in previous if d['phase']==c['kind'])
 assert used+c.get('minimum_remaining_heavy_seconds',0)<(300 if c['kind']=='protocol' else 7200),'CUMULATIVE_BUDGET'
 starts=0;started_ids=[]
 for p in runs.glob('gap149-*.started.json'):
  x=json.loads(p.read_text())
  if x['affinity']==[0]:continue
  cmd=x['command'];assert cmd[-2]=='--config','STARTED_CONFIG_UNKNOWN'
  old=json.loads(Path(cmd[-1]).read_text())
  if old['kind']!='ai' or not old.get('games'):continue
  result=runs/old['run_id']/'browser-result.json'
  if not result.exists():result=result.with_name('partial-browser-result.json')
  assert result.exists(),'OLD_ATTEMPT_COUNT_UNKNOWN'
  d=json.loads(result.read_text());starts+=d['started_games'];started_ids.extend(g['id'] for g in d['games'])
 assert starts+len(c.get('games',[]))<=64,'GAME_START_CAP'
 assert not set(started_ids).intersection(g['id'] for g in c.get('games',[])),'SUCCESS_OR_STARTED_GAME_REPLACEMENT'
 current=0;seen=set()
 for f in [out,tool,tool.parents[1]/'research-data/ai-sigma/frame10-baseline-gap']:
  for p in f.rglob('*'):
   if p.is_file():
    z=p.stat();k=(z.st_dev,z.st_ino)
    if k not in seen:seen.add(k);current+=z.st_blocks*512
 assert current+c['forecast_bytes']<234881024,'STORAGE_FORECAST'
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'NEW_HEAVY_DEADLINE'
 return {'decision':'launch_allowed','before_child_spawn':True,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'recognized_metadata':metadata,'old144_current_same_identity':same,'old144_stop_SHA256':'223a4866d89cf68695503077111537bdd889a6db0af4691cde5b02f60bf938be','physical_RAM_headroom':mem,'parent_research_current':current_research,'operation_conservative_headroom':134217728,'current_allocated':current,'forecast':c['forecast_bytes'],'guard':234881024,'used_seconds':used,'previous_game_starts':starts,'old_unknown_not_reduced':True,'additional_reservation':0,'whole_host_background_and_fullperiod_not_proved':True}
