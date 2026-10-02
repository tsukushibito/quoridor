import json,os,time,datetime,hashlib,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'ai-sigma-local-move-quality/admission.py';sp=importlib.util.spec_from_file_location('readonlyPhysical',p);base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def decide(heavy,previous,readerror=False):
 if readerror:raise RuntimeError('READ_ERROR')
 if base.base.decide(heavy,previous) is not True:raise RuntimeError('FALSE_ADMISSION')
 return True
def admit(c,out,tool,runs):
 previous=[json.loads(p.read_text()) for p in runs.glob('fpu140-*.process.json')];decide([],previous)
 phase=c['kind'];heavy,metadata=base.physical_heavy_scan() if phase!='protocol' else ([],[]);decide(heavy,previous)
 same=[];mem={}
 if phase!='protocol':
  p=Path(c['dependency_stop']);d=json.loads(p.read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==c['dependency_stop_SHA256'],'DEPENDENCY_STOP_HASH'
  assert d['issue']=='quoridor-4lc.137' and d['source_write_stopped'] and d['outer_ownedwait_remainingunknown0'] and d['monitor_callback_stop'],'DEPENDENCY_STOP_FLAGS'
  assert not d['Model2_drop']['handles'] and not d['Model2_drop']['activeNN'] and not d['main_timers']['main_timers'] and not d['main_timers']['pending_messages'],'MODEL_TIMER_ZERO'
  assert d['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'BOOT_CHANGED'
  for x in d['identities']:
   try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   if int(s[19])==x.get('start_ticks',x.get('starttick')):same.append(x)
  assert not same,'DEPENDENCY_CURRENT_OWNED'
  mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','MemFree:'))}
  assert mem['MemAvailable'] >= (4294967296 if phase=='build' else 6442450944),'RAM_HEADROOM'
 used={k:0 for k in ['build','mechanism','quality','protocol']}
 for d in previous:used[d['phase']]+=(datetime.datetime.fromisoformat(d['end'])-datetime.datetime.fromisoformat(d['start'])).total_seconds()
 limits={'build':300,'mechanism':180,'quality':1440,'protocol':180}
 assert used[phase]+c.get('minimum_remaining_heavy_seconds',0)<=limits[phase],'PHASE_BUDGET'
 assert used['build']+used['mechanism']+used['quality']+c.get('minimum_remaining_heavy_seconds',0)<=1920,'TOTAL_BUDGET'
 if phase in ['mechanism','quality']:
  old=[]
  for p in runs.glob('fpu140-*.started.json'):
   d=json.loads(p.read_text());command=d['command']
   if command[-2]!='--config':continue
   prior=json.loads(Path(command[-1]).read_text())
   if prior['kind']!=phase:continue
   result=runs/prior['run_id']/'browser-result.json'
   assert result.exists(),'OLD_STARTED_DENOMINATOR_UNKNOWN'
   old.append(json.loads(result.read_text()))
  if phase=='mechanism':assert sum(x['started_requests'] for x in old)+len(c['searches'])<=6,'MECHANISM_REQUEST_CAP'
  else:assert sum(x['started_games'] for x in old)+len(c['games'])<=8,'QUALITY_ROLLOUT_CAP'
 current=0
 for f in [out,tool,tool.parents[1]/'research-data/ai-sigma/140-candidate-true-mean-fpu']:
  for p in f.rglob('*'):
   if p.is_file():current+=p.stat().st_blocks*512
 forecast=c.get('forecast_bytes',0);assert current+forecast<234881024,'STORAGE_FORECAST_GUARD'
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'NEW_HEAVY_DEADLINE'
 return {'decision':'launch_allowed','before_child_spawn':True,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'recognized_metadata':metadata,'dependency_current_same_identity':same,'dependency_SHA256':c['dependency_stop_SHA256'],'physical_RAM_headroom':mem,'current_allocated':current,'forecast':forecast,'guard':234881024,'used_phase_seconds':used,'old_unknown_not_reduced':True,'additional_reservation':0,'no_natural_or_allhost_guarantee':True}
