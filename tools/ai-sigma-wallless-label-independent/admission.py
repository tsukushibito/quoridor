import json,pathlib,datetime,hashlib,importlib.util
R=pathlib.Path(__file__).resolve().parents[2]
def launch_if_allowed(a,spawn):
 if not isinstance(a,dict) or a.get('decision')!='launch_allowed' or a.get('remaining_unknown')!=0 or a.get('ownership_confirmed') is not True:raise RuntimeError('ADMISSION_REFUSED')
 if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat(a['newjob_deadline']):raise RuntimeError('ADMISSION_DEADLINE')
 return spawn()
def admit(config,out,tool,runs):
 now=datetime.datetime.now(datetime.timezone.utc);assert now<datetime.datetime.fromisoformat(config['newjob_deadline'])
 previous=[json.loads(p.read_text()) for p in runs.glob('p143-*.process.json')];assert all(not p['remaining'] and not p['unknown_adopted'] for p in previous)
 P=R/'research-data/ai-sigma/142-wallless-oracle';b=(P/'runtime-source-stopped-before-report.json').read_bytes();stop=json.loads(b);fb=(P/'final-source-stop.json').read_bytes();final=json.loads(fb)
 assert hashlib.sha256(b).hexdigest()=='3dc910cd05a94ca4fc07c81920bba246ccf0ee224e4bc5d08197730dc7a03a31'
 assert hashlib.sha256(fb).hexdigest()=='071a90d7206ca4385aa708679e6c6e1344cf20a48f0a956673eda3745f160a70'
 assert stop['source_write_stopped'] and stop['node_browser_stopped'] and stop['scientific_generation_certification_stopped'] and stop['outerownedwait_remainingunknown0'] and final['post_scientific_helpers_terminated'] and final['outerownedwait_remainingunknown0']
 assert stop['boot']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 live=[]
 for i in stop['identities']:
  try:s=pathlib.Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==i['start_ticks']:live.append(i)
 assert not live
 restore=json.loads((P/'git-stream-restore-check.json').read_text());helper_live=[]
 for i in [{'pid':restore['self_pid'],'starttick':restore['self_starttick']}]+restore['commands']:
  try:s=pathlib.Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==i['starttick']:helper_live.append(i)
 assert not helper_live and len(restore['commands'])+1==7
 for p,h in final['source_hash_final'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 spec=importlib.util.spec_from_file_location('readonly134physical',R/'tools/ai-sigma-local-move-quality/admission.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);heavy,meta=m.physical_heavy_scan();assert not heavy
 mem=int(next(s.split()[1] for s in pathlib.Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024;assert mem>=6*1024**3
 size=sum(p.stat().st_blocks*512 for folder in [out,tool,R/'research-data/ai-sigma/143-wallless-label-independent'] for p in folder.rglob('*') if p.is_file());assert size+config['forecast_bytes']<7*1024**2
 before=json.loads((R/'research-data/ai-sigma/143-wallless-label-independent/input-and-binding.json').read_text());assert before['critic_artifact_current_allocated']+8*1024**2<112*1024**2
 return {'UTC':now.isoformat(),'decision':'launch_allowed','remaining_unknown':0,'ownership_confirmed':True,'newjob_deadline':config['newjob_deadline'],'142_runtime_identities_checked':len(stop['identities']),'142_current_same_identity':live,'142_restore_helpers_checked':7,'142_restore_helpers_current':helper_live,'142_final_owner_count':final['identities_checked'],'142_final_helpers_record_not_runtime_denominator':True,'external_heavy':heavy,'recognized_infrastructure':meta,'MemAvailable':mem,'own_current_allocated':size,'forecast':config['forecast_bytes'],'reservation_new':0,'old_unknown_not_decreased':True,'current_absence_not_natural_fullperiod':True}
