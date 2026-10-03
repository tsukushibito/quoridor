import json,os,time,datetime,hashlib,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parent.parent/'ai-sigma-local-move-quality/admission.py';sp=importlib.util.spec_from_file_location('readonlyPhysical',p);base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
def size(bases):
 seen=set();n=0
 for basepath in bases:
  for p in basepath.rglob('*'):
   if p.is_file():
    s=p.stat();k=(s.st_dev,s.st_ino)
    if k not in seen:seen.add(k);n+=s.st_blocks*512
 return n
def admit(c,out,tool,runs):
 assert c['issue']=='quoridor-4lc.163' and c['frame']==10
 prev=[json.loads(p.read_text()) for p in runs.glob('cycle163-*.process.json')];assert base.base.decide([],prev) is True,'OWN_OLD_NOT_ZERO'
 heavy,meta=base.physical_heavy_scan() if c['kind']=='browser' else ([],[]);assert base.base.decide(heavy,prev) is True,'EXTERNAL_HEAVY_UNKNOWN'
 root=tool.parents[1];stop=root/'research-data/ai-sigma/151-sigma-web-port/runtime-source-stopped-before-report.json';assert hashlib.sha256(stop.read_bytes()).hexdigest()=='c6868015bac31ea2e975ed384675bc0ad8b16a39b0c9aae566c5cef0ff0b297e';d=json.loads(stop.read_text());assert d['science_source_write_stopped'] and not d['current_same_identity'] and not d['owned_remainingunknown'];assert d['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 ids=[]
 for p in (root/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs').glob('port151-*.process.json'):
  x=json.loads(p.read_text());assert not x['remaining'] and not x['unknown_adopted'];ids.extend(x['tracked']);ids.append({'pid':x['runner_pid'],'start_ticks':x['runner_starttick']})
 current=[]
 for x in ids:
  try:s=Path('/proc/'+str(x['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==x['start_ticks']:current.append(x)
 assert not current,'OLD151_CURRENT_IDENTITY'
 for p,h in d['science_source_same_afterhash'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,'OLD151_SOURCE_CHANGED'
 s156=root/'research-data/ai-sigma/156-nnue-feature-cost/science-stop.json';z156=json.loads(s156.read_text());assert z156['scientific_source_write_stopped'] and not z156['current_same_identity'];
 for p,h in z156['source_current'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,'OLD156_SOURCE_CHANGED'
 for f in (root/'.artifacts/ai-sigma/resume-20261003/NNUE-FEATURE-COST/runs').glob('*.process.json'):
  z=json.loads(f.read_text());assert not z['remaining'] and not z['unknown_adopted'];
  for x in z['tracked']+[{'pid':z['runner_pid'],'start_ticks':z['runner_starttick']}]:
   try:st=Path('/proc/'+str(x['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(st[19])!=x['start_ticks'],'OLD156_CURRENT_IDENTITY'
 old159=root/'research-data/ai-sigma/159-cpu-concurrency/science-stop.json';z159=json.loads(old159.read_text());assert z159['scientific_source_write_stopped'];
 for p,h in z159['source_hashes'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,'OLD159_SOURCE_CHANGED'
 for f in (root/'.artifacts/ai-sigma/resume-20261003/CPU-CONCURRENCY/runs').glob('*.process.json'):
  z=json.loads(f.read_text());assert not z['remaining'] and not z['unknown_adopted'];
  for x in z['tracked']+[{'pid':z['runner_pid'],'start_ticks':z['runner_starttick']}]:
   try:st=Path('/proc/'+str(x['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
   except FileNotFoundError:continue
   assert int(st[19])!=x['start_ticks'],'OLD159_CURRENT_IDENTITY'
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;assert mem>4294967296,'PHYSICAL_RAM'
 research=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try:s=(p/'stat').read_text().rsplit(')',1)[1].split();args=(p/'cmdline').read_bytes();
  except (FileNotFoundError,ProcessLookupError):continue
  if s[0]!='Z' and (b'/tools/ai-sigma-' in args or b'/tools/research-team/' in args):research.append({'pid':int(p.name),'starttick':int(s[19]),'RSS':int(s[21])*4096})
 assert sum(x['RSS'] for x in research)+4294967296+134217728<8589934592,'PARENT_RAM'
 
 # 4core condition is physical compute/owner, never LLM active-count.
 if len(c.get('mode',{}).get('cores',[]))==4:
  for x in research:
   pid=x['pid'];argv=[v.decode() for v in Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\0') if v]
   if argv and Path(argv[0]).name.startswith(('python','node')) and any('/tools/ai-sigma-' in a for a in argv[1:]) and os.sched_getaffinity(pid)-set(c['mode']['cores']):raise RuntimeError('MODE4_EXTERNAL_CALCULATION_POOL_CONFLICT')
 own=size([tool,out,root/'research-data/ai-sigma/163-fixed-cycle']);old=size([root/'tools/ai-sigma-nnue-feature-cost',root/'.artifacts/ai-sigma/resume-20261003/NNUE-FEATURE-COST',root/'research-data/ai-sigma/156-nnue-feature-cost',root/'tools/ai-sigma-sigma-web-port',root/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT',root/'research-data/ai-sigma/151-sigma-web-port',root/'tools/ai-sigma-baseline-gap-frame10',root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP',root/'research-data/ai-sigma/frame10-baseline-gap']);assert own+c['forecast_bytes']<29360128 and own+c['forecast_bytes']+old<2147483648,'STORAGE_FORECAST'
 assert time.time()<datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp(),'DEADLINE'
 used=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in prev if x['phase']==c['kind']);assert used<({'browser':180,'protocol':120}[c['kind']]),'BUDGET'
 return {'decision':'launch_allowed','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_child_spawn':True,'external_heavy':heavy,'metadata':meta,'old151_current_identity':current,'old151_stop_SHA256':hashlib.sha256(stop.read_bytes()).hexdigest(),'RAM_available':mem,'research_current':research,'own_current':own,'own_forecast':c['forecast_bytes'],'own_guard':29360128,'old149_151_retained_current':old,'old_unknown_not_reduced':True,'additional_reservation':0,'used_seconds':used,'not_full_host_or_period_proof':True}
