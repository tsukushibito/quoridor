import json,pathlib,os,datetime,importlib.util,hashlib
R=pathlib.Path(__file__).resolve().parents[2]
def launch_if_allowed(admission,spawn):
 if not isinstance(admission,dict) or admission.get('decision')!='launch_allowed' or admission.get('remaining_unknown')!=0 or admission.get('ownership_confirmed') is not True:raise RuntimeError('ADMISSION_REFUSED')
 if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat(admission['newjob_deadline']):raise RuntimeError('ADMISSION_DEADLINE')
 return spawn()
def admit(config,out,tool,runs):
 now=datetime.datetime.now(datetime.timezone.utc);assert now<datetime.datetime.fromisoformat(config['newjob_deadline']),'ADMISSION_DEADLINE'
 previous=[json.loads(p.read_text()) for p in runs.glob('p142-*.process.json')];assert all(not x['remaining'] and not x['unknown_adopted'] for x in previous),'OWN_STOP_UNKNOWN'
 p=R/'research-data/ai-sigma/140-candidate-true-mean-fpu/runtime-source-stopped-before-report.json';raw=p.read_bytes();stop=json.loads(raw)
 assert stop['source_write_stopped'] and stop['scientific_run_stopped'] and stop['outer_ownedwait_remainingunknown0'] and not stop['current_same_identity'],'140_STOP_UNCONFIRMED'
 assert all(not j['remaining'] and not j['unknown_adopted'] for j in stop['jobs']),'140_JOB_STOP_UNKNOWN'
 assert stop['boot']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'140_BOOT_CHANGED'
 live=[]
 for x in stop['identities']:
  try:s=pathlib.Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==x['start_ticks']:live.append(x)
 assert not live,'140_STILL_OWNED'
 spec=importlib.util.spec_from_file_location('readonly134physical',R/'tools/ai-sigma-local-move-quality/admission.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 heavy,metadata=m.physical_heavy_scan();assert not heavy,'EXTERNAL_HEAVY'
 mem=int(next(s.split()[1] for s in pathlib.Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024;assert mem>=6442450944,'RAM_HEADROOM'
 size=sum(p.stat().st_blocks*512 for d in [out,tool,R/'research-data/ai-sigma/142-wallless-oracle'] for p in d.rglob('*') if p.is_file())
 report=R/'docs/reports/ai-sigma-hypothesis-wallless-oracle.md'
 if report.exists():size+=report.stat().st_blocks*512
 assert 8908800+size+config['forecast_bytes']<14680064,'COMBINED_STORAGE_FORECAST'
 return {'decision':'launch_allowed','UTC':now.isoformat(),'before_child_spawn':True,'dependency140_stop_path':str(p),'dependency140_stop_sha256':hashlib.sha256(raw).hexdigest(),'140_identities_checked':len(stop['identities']),'140_current_same_identity':live,'external_heavy':heavy,'recognized_infrastructure':metadata,'physical_MemAvailable':mem,'own_allocated':size,'old_conservative_held':8908800,'combined_forecast':8908800+size+config['forecast_bytes'],'forecast_bytes':config['forecast_bytes'],'reservation_new':0,'old_unknown_not_decreased':True,'full_host_resources_not_certified':True,'remaining_unknown':0,'ownership_confirmed':True,'newjob_deadline':config['newjob_deadline']}
