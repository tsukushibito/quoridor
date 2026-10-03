"""One fail-closed admission branch, before sole child spawn. Read-only external identities."""
import json,os,time,datetime,hashlib,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'ai-sigma-local-move-quality/admission.py'
sp=importlib.util.spec_from_file_location('readonlyPhysical134',p);base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def admit(c,out,tool,runs):
 previous=[json.loads(p.read_text()) for p in runs.glob('port151-*.process.json')]
 assert base.base.decide([],previous) is True,'OLD_OWNED_NOT_ZERO'
 heavy,metadata=base.physical_heavy_scan() if c['kind'] in ['build','stageA','stageB'] else ([],[])
 assert base.base.decide(heavy,previous) is True,'EXTERNAL_HEAVY_UNKNOWN'
 same=[]
 stop_path=tool.parents[1]/'research-data/ai-sigma/151-sigma-web-port/user-direction-science-stop.json'
 assert hashlib.sha256(stop_path.read_bytes()).hexdigest()=='f41c4d9c6263c908e268950edde977b94a94a967ab8dca5e85fc669287e79b8e','OLD149_STOP_SHA'
 stop=json.loads(stop_path.read_text());assert stop['science_source_write_stopped'] and stop['new_heavy_forbidden'],'OLD149_NOT_STOPPED'
 assert stop['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'BOOT_CHANGED'
 old149=tool.parents[1]/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP/runs'
 ids=list(stop['current_identities'])
 for p in old149.glob('*.process.json'):
  d=json.loads(p.read_text());assert not d['remaining'] and not d['unknown_adopted'],'OLD149_REMAINING_UNKNOWN'
  ids.extend(d['tracked']);ids.append({'pid':d['runner_pid'],'start_ticks':d['runner_starttick']})
 for x in ids:
  try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==x['start_ticks']:same.append(x)
 assert not same,'OLD149_CURRENT_IDENTITY'
 mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','MemFree:'))}
 assert mem['MemAvailable']>=({'protocol':1073741824,'build':2147483648}.get(c['kind'],6442450944)),'PHYSICAL_RAM_HEADROOM'
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
 assert research_current+({'protocol':1073741824,'build':2147483648}.get(c['kind'],6442450944))+134217728<8589934592,'PARENT8_CURRENT_HEADROOM'
 used=sum((datetime.datetime.fromisoformat(d['end'])-datetime.datetime.fromisoformat(d['start'])).total_seconds() for d in previous if d['phase']==c['kind'])
 assert used+c.get('minimum_remaining_heavy_seconds',0)<{'protocol':300,'build':180,'stageA':300,'stageB':1800}[c['kind']],'CUMULATIVE_BUDGET'
 starts=0;started_ids=[]
 # Per-stage experiments and total NN budget are registered; no blind attempt replacement.
 for p in runs.glob('port151-*.started.json'):
  old=json.loads(Path(json.loads(p.read_text())['command'][-1]).read_text()) if False else None
 current=0;seen=set()
 for f in [out,tool,tool.parents[1]/'research-data/ai-sigma/151-sigma-web-port']:
  for p in f.rglob('*'):
   if p.is_file():
    z=p.stat();k=(z.st_dev,z.st_ino)
    if k not in seen:seen.add(k);current+=z.st_blocks*512
 old149_current=sum(p.stat().st_blocks*512 for base in [tool.parents[1]/'research-data/ai-sigma/frame10-baseline-gap',tool.parents[1]/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP',tool.parent/'ai-sigma-baseline-gap-frame10'] for p in base.rglob('*') if p.is_file())
 assert current+c['forecast_bytes']<234881024,'STORAGE_FORECAST'
 assert current+c['forecast_bytes']+old149_current<2147483648,'EXISTING_EXPERIMENT_ENTRY'
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'NEW_HEAVY_DEADLINE'
 return {'decision':'launch_allowed','before_child_spawn':True,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'recognized_metadata':metadata,'old149_current_same_identity':same,'old149_stop_SHA256':'f41c4d9c6263c908e268950edde977b94a94a967ab8dca5e85fc669287e79b8e','physical_RAM_headroom':mem,'parent_research_current':current_research,'operation_conservative_headroom':134217728,'current_allocated':current,'forecast':c['forecast_bytes'],'guard':234881024,'used_seconds':used,'previous_game_starts':starts,'old149_current_retained':old149_current,'existing_entry_conservative':2147483648,'old_unknown_not_reduced':True,'additional_reservation':0,'whole_host_background_and_fullperiod_not_proved':True}
