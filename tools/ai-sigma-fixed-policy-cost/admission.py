import json,os,time,hashlib,datetime
from pathlib import Path
import importlib.util
p=Path(__file__).resolve().parent.parent/'ai-sigma-local-move-quality/admission.py';sp=importlib.util.spec_from_file_location('readonly134admission',p);base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def decide(heavy,previous,read_error=False,dependency_zero=True):
 if read_error or not dependency_zero:raise RuntimeError('UNCONFIRMED_ADMISSION')
 base.base.decide(heavy,previous)
 return True
def admit(config,out,tool,runs):
 previous=[json.loads(p.read_text()) for p in runs.glob('cost137-*.process.json')];decide([],previous)
 heavy,metadata=base.physical_heavy_scan() if config['kind']!='protocol' else ([],[]);decide(heavy,previous)
 same=[];memory={}
 if config['kind']!='protocol':
  stop_path=Path(config['dependency_stop']);stop=json.loads(stop_path.read_text())
  if hashlib.sha256(stop_path.read_bytes()).hexdigest()!=config['dependency_stop_SHA256']:raise RuntimeError('DEPENDENCY135_SHA')
  if stop['issue']!='quoridor-4lc.135' or not stop['source_write_stopped'] or not stop['outer_remaining_unknown0'] or not stop['monitor_callback_stop'] or any(x['remaining'] or x['unknown_adopted'] for x in stop['jobs']):raise RuntimeError('DEPENDENCY135_NOT_STOPPED')
  if stop['boot']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():raise RuntimeError('BOOT_CHANGED')
  ids=json.loads(Path(config['dependency_identities']).read_text())
  for ref in ids['process_refs']:
   if hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()!=ref['SHA256']:raise RuntimeError('DEPENDENCY_PROCESS_CHANGED')
  for x in ids['identities']:
   try:st=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   if int(st[19])==x['start_ticks']:same.append(x)
  if same:raise RuntimeError('DEPENDENCY135_CURRENT_OWNED')
  memory={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemAvailable:','MemFree:'))}
  if memory['MemAvailable']<6442450944:raise RuntimeError('RAM_HEADROOM')
  count=0
  for p in runs.glob('cost137-*.started.json'):
   d=json.loads(p.read_text());finished=next((q for q in previous if q['name']==p.name.replace('.started.json','')),None)
   if finished and finished['phase']=='protocol':continue
   if d['command'][-2]!='--config':raise RuntimeError('PREVIOUS_STARTED_CONFIG_UNKNOWN')
   c=json.loads(Path(d['command'][-1]).read_text())
   if c['kind']=='protocol':continue
   result=runs/c['run_id']/'browser-result.json'
   if not result.is_file():raise RuntimeError('PREVIOUS_STARTED_REQUEST_COUNT_UNKNOWN')
   count+=json.loads(result.read_text())['started_requests']
  if count+4>4:raise RuntimeError('REQUEST_CAP')
 current=sum(p.stat().st_blocks*512 for f in [out,tool,tool.parents[1]/'research-data/ai-sigma/137-fixed-policy-cost'] for p in f.rglob('*') if p.is_file())
 forecast=0 if config['kind']=='protocol' else config['forecast_bytes']
 if current+forecast>=58720256:raise RuntimeError('STORAGE_HEADROOM')
 if time.time()>=datetime.datetime.fromisoformat(config['newjob_deadline']).timestamp():raise RuntimeError('NEWJOB_DEADLINE')
 used=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in previous if x['phase']!='protocol')
 if config['kind']!='protocol' and used+config['minimum_remaining_heavy_seconds']>180:raise RuntimeError('HEAVY_BUDGET')
 return {'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'recognized_metadata':metadata,'dependency_same_identity':same,'dependency_SHA256':config['dependency_stop_SHA256'],'physical_RAM_headroom':memory,'current_allocated':current,'forecast':forecast,'guard':58720256,'heavy_used_seconds':used,'remaining_heavy_seconds':180-used,'decision':'launch_allowed','before_child_spawn':True,'whole_host_no_load_not_proved':True,'unknown_old_holdings_reduced':False,'reservation_added':0}
