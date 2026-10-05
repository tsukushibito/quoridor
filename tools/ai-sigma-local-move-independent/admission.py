import json,pathlib,os,datetime,importlib.util
R=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('readonly134physical',R/'tools/ai-sigma-local-move-quality/admission.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def admit(config,out,tool,runs):
 now=datetime.datetime.now(datetime.timezone.utc);assert now<datetime.datetime.fromisoformat(config['newjob_deadline']),'ADMISSION_DEADLINE'
 previous=[json.loads(p.read_text()) for p in runs.glob('p135-*.process.json')];assert all(not x['remaining'] and not x['unknown_adopted'] for x in previous),'OWN_STOP_UNKNOWN'
 p=R/'research-data/ai-sigma/134-local-move-quality/runtime-source-stopped-before-report.json';stop=json.loads(p.read_text());assert stop['source_runtime_stopped'] and not stop['current_same_identity'] and not stop['remaining_unknown'],'134_STOP_UNCONFIRMED';assert stop['boot']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'134_BOOT_CHANGED'
 live=[]
 for x in stop['identities']:
  try:s=pathlib.Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==x['start_ticks']:live.append(x)
 assert not live,'134_STILL_OWNED'
 heavy,metadata=m.physical_heavy_scan();assert not heavy,'EXTERNAL_HEAVY'
 mem=int(next(s.split()[1] for s in pathlib.Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024;assert mem>=6442450944,'RAM_HEADROOM'
 size=sum(p.stat().st_blocks*512 for d in [out,tool,R/'research-data/ai-sigma/135-local-move-independent'] for p in d.rglob('*') if p.is_file());assert size+config['forecast_bytes']<29360128,'OWN_STORAGE_HEADROOM'
 # Existing critic artifact holding and this allocation use the same reservation; unknown old holding is retained.
 total=0;seen=set()
 for parent in [R/'.artifacts/ai-sigma/continuation-20261001',R/'.artifacts/ai-sigma/resume-20261002']:
  for d in parent.iterdir():
   if not d.is_dir() or not any(n in d.name for n in ['CRITIC','INDEPENDENT','EVALUATION-PLAN']):continue
   for p in d.rglob('*'):
    if p.is_file():
     st=p.stat();key=st.st_dev,st.st_ino
     if key not in seen:seen.add(key);total+=st.st_blocks*512
 assert total+config['forecast_bytes']<117440512,'COMBINED_ARTIFACT_HEADROOM'
 return {'decision':'launch_allowed','UTC':now.isoformat(),'before_child_spawn':True,'134_identities_current0':len(stop['identities']),'134_stop_path':str(R/'research-data/ai-sigma/134-local-move-quality/runtime-source-stopped-before-report.json'),'external_heavy':heavy,'recognized_infrastructure':metadata,'physical_MemAvailable':mem,'own_allocated':size,'combined_critic_artifact_allocated':total,'forecast_bytes':config['forecast_bytes'],'reservation_new':0,'old_unknown_not_decreased':True,'full_host_resources_not_certified':True}
