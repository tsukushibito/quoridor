import pathlib,json,datetime,hashlib,tarfile,os
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/DEEP-NODE-INDEPENDENT';T=R/'tools/ai-sigma-deep-node-independent';D=R/'research-data/ai-sigma/133-deep-node-independent';sha=lambda b:hashlib.sha256(b).hexdigest();jobs=[];ids=set()
for p in (O/'runs').glob('p133-*.process.json'):
 d=json.loads(p.read_text());jobs.append({k:d[k] for k in ['name','start','end','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','remaining','unknown_adopted','all_observed_TIDs_at_assigned_CPU']})
 for x in d['tracked']+[{'pid':d['runner_pid'],'start_ticks':d['runner_starttick']}]:ids.add((x['pid'],x['start_ticks']))
live=[]
for p,t in ids:
 try:
  s=pathlib.Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()
  if int(s[19])==t:live.append({'pid':p,'starttick':t})
 except FileNotFoundError:pass
assert not live and all(not x['remaining'] and not x['unknown_adopted'] for x in jobs)
before=json.loads((O/'input-before.json').read_text());after={}
for p,h in before['checks'].items():
 if p.startswith(str(R)):
  v=sha(pathlib.Path(p).read_bytes());assert v==h;after[p]=v
for x in before['source']:
 assert sha((R/x['path']).read_bytes())==x['sha256'];after[x['path']]=x['sha256']
model=R/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';assert sha(model.read_bytes())==before['model_SHA'];after[str(model)]=before['model_SHA']
(O/'input-after.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'currentmatch':after,'original_write0':True},indent=2)+'\n')
(O/'failures.json').write_text(json.dumps({'helper_admission_failures':2,'initial_causes':['all /proc exe required: root/sshd permissions and disappearing process','sshd argv0 contains full process title, not bare binary name; transient PID exe failure'], 'command_control_failure':'admission exited1 but next shell command launched runner; no conjunction/checked return','new_count_run_executed':True,'successful_launch_admission_claim':False,'runtimeguard_success_distinct':True,'signal_attempt':'runner already absent before owned SIGTERM, no signal sent','producer_failures':0,'searches_planned':4,'completed':4,'unexecuted':0,'no_good_result_repeat':True,'no_NN_mismatch_from_helper':True},indent=2)+'\n')
run=O/'runs/p133-count-r1'
stop={'issue':'quoridor-4lc.133','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'jobs':jobs,'identity_count':len(ids),'current_same_identity':live,'currentabsence_not_natural_allperiod':True,'source_write_stopped':True,'source':{str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()},'Model2_drop':json.loads((run/'model-drop.json').read_text()),'main_timers':json.loads((run/'main-timers-stop.json').read_text()),'monitor_callback':json.loads((run/'monitor-stop.json').read_text()),'inner_controlled':json.loads((run/'controlled-stop.json').read_text()),'outer_remaining_unknown0':True,'managed_guard_observations_not_launch_admission':True,'input_after_currentmatch':len(after),'same_identity_ownership_proof_scope':'managed jobs; short intake/read/closure command process evidence incomplete'}
(D/'runtime-source-stopped-before-report.json').write_text(json.dumps(stop,indent=2)+'\n')
for n in ['config.json','static-config.json','input-before.json','input-after.json','admission.json','source-audit.json','failures.json']:(D/n).write_bytes((O/n).read_bytes())
for n in ['independent-saved','independent-new','summary','clock-end','startup']:(D/(n+'.json')).write_bytes((run/(n+'.json')).read_bytes())
archive=D/'own-run-evidence.tar.gz';members=[]
with tarfile.open(archive,'w:gz') as a:
 for p in sorted((O/'runs').rglob('*')):
  if not p.is_file() or '/t/' in str(p) or '/xdg-' in str(p):continue
  b=p.read_bytes();name=str(p.relative_to(O));a.add(p,arcname=name,recursive=False);members.append({'path':name,'SHA256':sha(b),'bytes':len(b)})
with tarfile.open(archive) as a:
 for m in a.getmembers():assert sha(a.extractfile(m).read())==next(x['SHA256'] for x in members if x['path']==m.name)
(D/'archive-manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.133','archive':archive.name,'SHA256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,'members':members,'allmemberrestore_match':True,'source_raw_reference':'research-data/ai-sigma/132-deep-node-comparison/all-attempts.tar.gz','source_archive_SHA256':before['checks'][str(R/'research-data/ai-sigma/132-deep-node-comparison/all-attempts.tar.gz')],'upstream_raw_copy_saved0':True},indent=2)+'\n')
# Remove only own unused reproductions after browser read and immutable reference binding; upstream untouched.
cleaned=[]
for n in ['browser-result.json','baseline.wasm','trace.wasm']:
 p=O/n;cleaned.append({'path':str(p.relative_to(R)),'SHA256':sha(p.read_bytes()),'bytes':p.stat().st_size,'regeneration':'prepare.py -> immutable original archive; owned browser stopped'});p.unlink()
(D/'own-unused-expansion-cleanup.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':cleaned,'upstream_delete0':True},indent=2)+'\n')
print(json.dumps({'current0':len(ids),'inputafter':len(after),'archive_bytes':archive.stat().st_size,'members':len(members),'stopSHA':sha((D/'runtime-source-stopped-before-report.json').read_bytes()),'jobs':jobs}))
