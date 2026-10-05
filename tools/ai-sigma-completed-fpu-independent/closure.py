import pathlib,json,hashlib,tarfile,datetime,os
R=pathlib.Path(__file__).resolve().parents[2]; O=R/'.artifacts/ai-sigma/resume-20261002/COMPLETED-FPU-INDEPENDENT';T=R/'tools/ai-sigma-completed-fpu-independent';D=R/'research-data/ai-sigma/125-completed-fpu-independent';D.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def identities(x,z):
 if isinstance(x,dict):
  pid=x.get('pid',x.get('runner_pid'));tick=x.get('start_ticks',x.get('starttick',x.get('runner_starttick')))
  if isinstance(pid,int) and isinstance(tick,int):z.add((pid,tick))
  if isinstance(x.get('child_pid'),int) and isinstance(x.get('child_starttick'),int):z.add((x['child_pid'],x['child_starttick']))
  for v in x.values():identities(v,z)
 elif isinstance(x,list):
  for v in x:identities(v,z)
def current(z):
 live=[]
 for p,t in z:
  try:
   s=pathlib.Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()
   if int(s[19])==t:live.append({'pid':p,'starttick':t,'state':s[0]})
  except (FileNotFoundError,ProcessLookupError):pass
 return live
before=read(O/'input-before.json')['checks'];af={}
with tarfile.open(R/'research-data/ai-sigma/123-completed-fpu/runs-all-attempts.tar.gz','r:gz') as a:
 for p,h in before.items():
  b=a.extractfile(p).read() if p.startswith('runs/') else (R/p).read_bytes();af[p]={'before':h,'after':sha(b),'equal':h==sha(b)}
assert all(x['equal'] for x in af.values());save(O/'input-after.json',{'checks':af,'all_equal':True})
z=set();jobs=[]
for p in (O/'runs').glob('*.process.json'):
 d=read(p);identities(d,z);jobs.append({k:d.get(k) for k in ['name','phase','start','end','exit','stop_reason','remaining','unknown_adopted','peak_group_plus_runner_RSS','peak_allocated_bytes']})
for p in (O/'runs').glob('*/controlled-stop.json'):identities(read(p),z)
old=set();identities(read(O/'original-small-stop.json'),old)
assert not current(z) and not current(old)
model=read(O/'runs/p125-count-r1/model-drop.json');timers=read(O/'runs/p125-count-r1/main-timers-stop.json')
stop={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual_NN_ended_by':read(O/'runs/p125-count-r1.process.json')['end'],'own_identities':len(z),'own_identity_current':current(z),'original_subset_identities':len(old),'original_subset_current':current(old),'original_before_union139_current0':'input-before.json','jobs':jobs,'Modeldrop':model,'main_timers':timers,'inner_controlled':'runs/p125-count-r1/controlled-stop.json','outer_wait':'runs/p125-count-r1.process.json','monitor_callback':'runs/p125-count-r1/pause-monitor-stop.json','source_SHA256':{str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()},'source_and_heavy_write_stopped':True,'forced_not_natural_all_period_proof':True,'new_game':0,'actual_go':False}
save(O/'runtime-source-stopped-before-report.json',stop)
save(O/'denominator-clarification.json',{'primary_actual_search_attempts':4,'completed':4,'backup':128,'hand_NN':128,'startup_NN':6,'total_NN':134,'terminal_noNN':0,'match_only_run':'p125-match-nn0','match_only_NN':0,'match_only_actual_search_attempts':0,'summary_planned4_completed0_is_generic_wrapper_metadata_not_4_more_unperformed_searches':True,'old15_not_replaced':True})
for n in ['runtime-source-stopped-before-report.json','input-before.json','input-after.json','selection-preregister.json','actual-served-source-bindings.json','denominator-clarification.json','config.json','match-config.json','source-audit-config.json','diagnose-r1-to-match.diff']:(D/n).write_bytes((O/n).read_bytes())
files=[]
for p in O.rglob('*'):
 if p.is_file() and not any('p125-closure' in x for x in p.relative_to(O).parts) and not any(x in p.relative_to(O).parts for x in ['t','xdg-cache','xdg-config','private-index']):files.append(p)
archive=D/'runs-and-evidence.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for p in sorted(files):a.add(p,arcname=str(p.relative_to(O)),recursive=False)
checks=[]
with tarfile.open(archive,'r:gz') as a:
 for m in a.getmembers():
  if m.isfile():b=a.extractfile(m).read();assert b==(O/m.name).read_bytes();checks.append({'member':m.name,'SHA256':sha(b),'bytes':len(b)})
save(D/'archive-manifest.json',{'issue':'quoridor-4lc.125','archive':archive.name,'SHA256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,'members':checks,'restored_all_members_match':True,'source':'tools/ai-sigma-completed-fpu-independent','upstream_data_Git':'6e7e338c79e4be11f6a75a0df452e5df736e8ba9','upstream_handoff_Git':'7bb4874','note':'ongoing closure job metadata copied directly after completion; shared model no copy'})
print(json.dumps({'own_identities':len(z),'old_subset':len(old),'current0':True,'input_checks':len(af),'archive_bytes':archive.stat().st_size,'archive_members':len(checks),'stop_SHA256':sha((O/'runtime-source-stopped-before-report.json').read_bytes())}))
