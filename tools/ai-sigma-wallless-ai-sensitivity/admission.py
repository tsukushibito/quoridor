import json,os,time,datetime,hashlib,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'ai-sigma-local-move-quality/admission.py';sp=importlib.util.spec_from_file_location('readonlyPhysical',p);base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def admit(c,out,tool,runs):
 previous=[json.loads(p.read_text()) for p in runs.glob('wallless144-*.process.json')]
 assert base.base.decide([],previous) is True,'PREVIOUS_NOT_ZERO'
 heavy,metadata=base.physical_heavy_scan() if c['kind']=='ai' else ([],[])
 assert base.base.decide(heavy,previous) is True,'EXTERNAL_HEAVY_UNKNOWN'
 same=[];dependency={}
 if c['kind']=='ai':
  for key in ['dependency_stop','dependency_verdict']:
   p=Path(c[key]);assert hashlib.sha256(p.read_bytes()).hexdigest()==c[key+'_SHA256'],'DEPENDENCY_SHA'
   dependency[key]=json.loads(p.read_text())
  d=dependency['dependency_stop'];assert d['issue']=='quoridor-4lc.143','STOP_ISSUE'
  v=dependency['dependency_verdict'];assert v['finite_supported'] and v['NN']==0,'LABEL_NOT_SUPPORTED'
  for raw in v['raw_bindings']:
   assert hashlib.sha256(Path(raw['path']).read_bytes()).hexdigest()==raw['SHA256'],'VERDICT_RAW_CHANGED'
  assert c['dependency_input_hashes']==c['registered_input_hashes'],'INPUT_SHA_NOT_SAME'
  # actual stop schema bound by config only after inspected finite stop record
  assert c['dependency_stop_zero_confirmed'] is True,'STOP_NOT_ZERO'
  assert d['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'BOOT_CHANGED'
  assert not d['job']['remaining'] and not d['job']['unknown_adopted'] and not d['remaining_unknown'],'OUTER_NOT_ZERO'
  assert d['browser_status']['Model']==0 and d['browser_status']['NN']==0 and not d['browser_status']['main_active'] and d['browser_status']['timer_message']==0,'BROWSER_NOT_ZERO'
  assert d['scientific_source_write_stopped'] and not d['monitor_stop']['active_monitor_timer'] and not d['monitor_stop']['pending_children'] and d['inner_controlled']['waited'] and not d['inner_controlled']['remaining_pids'],'STOP_FLAGS'
  assert not d['outer_ack']['unknown_adopted'] and not d['outer_ack']['registered_live'],'OUTER_ACK'
  ids=[*d['job']['tracked'],{'pid':d['job']['runner_pid'],'start_ticks':d['job']['runner_starttick']}]+d['inner_controlled']['tracked']
  for x in ids:
   try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   if int(s[19])==x.get('start_ticks',x.get('starttick')):same.append(x)
  assert not same,'DEPENDENCY_CURRENT_OWNED'
 mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','MemFree:'))}
 assert mem['MemAvailable'] >= (1073741824 if c['kind']=='protocol' else 6442450944),'RAM_HEADROOM'
 used=sum((datetime.datetime.fromisoformat(d['end'])-datetime.datetime.fromisoformat(d['start'])).total_seconds() for d in previous if d['phase']==c['kind'])
 assert used+c.get('minimum_remaining_heavy_seconds',0)<(180 if c['kind']=='protocol' else 120),'CUMULATIVE_BUDGET'
 if c['kind']=='ai':
  started=0
  for p in runs.glob('wallless144-*.started.json'):
   x=json.loads(p.read_text());cmd=x['command']
   if x['affinity']==[0]:continue
   assert cmd[-2]=='--config','STARTED_CONFIG_UNKNOWN'
   old=json.loads(Path(cmd[-1]).read_text())
   if old['kind']!='ai':continue
   result=runs/old['run_id']/'browser-result.json';assert result.exists(),'OLD_ATTEMPTS_UNKNOWN'
   started+=json.loads(result.read_text())['started_requests']
  assert started+len(c['searches'])<=6,'REQUEST_CAP'
 current=0
 for f in [out,tool,tool.parents[1]/'research-data/ai-sigma/144-wallless-ai-sensitivity']:
  for p in f.rglob('*'):
   if p.is_file():current+=p.stat().st_blocks*512
 assert current+c['forecast_bytes']<58720256,'STORAGE_FORECAST'
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'DEADLINE'
 return {'decision':'launch_allowed','before_child_spawn':True,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'recognized_metadata':metadata,'dependency_current_same_identity':same,'dependency_bindings':{k:c.get(k+'_SHA256') for k in dependency},'physical_RAM_headroom':mem,'current_allocated':current,'forecast':c['forecast_bytes'],'guard':58720256,'used_seconds':used,'old_unknown_not_reduced':True,'additional_reservation':0}
