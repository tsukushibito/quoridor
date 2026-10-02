import json,pathlib,datetime,hashlib,tarfile
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/TACTICAL-SAVED-INDEPENDENT';D=R/'research-data/ai-sigma/131-tactical-saved-independent';T=R/'tools/ai-sigma-tactical-saved-independent';sha=lambda b:hashlib.sha256(b).hexdigest()
ids=set();jobs=[]
for p in (O/'runs').glob('p131-*.process.json'):
 d=json.loads(p.read_text());jobs.append({k:d[k] for k in ['name','start','end','exit','peak_group_plus_runner_RSS','peak_allocated_bytes','remaining','unknown_adopted']})
 for x in d['tracked']+[{'pid':d['runner_pid'],'start_ticks':d['runner_starttick']}]:ids.add((x['pid'],x['start_ticks']))
live=[]
for p,t in ids:
 try:
  s=pathlib.Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()
  if int(s[19])==t:live.append({'pid':p,'starttick':t})
 except (FileNotFoundError,ProcessLookupError):pass
assert not live
stop={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':'quoridor-4lc.131','boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'managed_previous_jobs':jobs,'same_identity_count':len(ids),'same_identity_current':live,'source_hashes':{str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()},'source_write_stopped':True,'Chrome':0,'NN':0,'model_load':0,'new_browser_functional_success':False,'closure_current_root_excluded_until_process_metadata_final':True,'currentabsence_not_natural_or_all_period':True}
(D/'runtime-source-stopped-before-report.json').write_text(json.dumps(stop,indent=2)+'\n')
for p in O.iterdir():
 if p.is_file() and p.suffix in ['.json','.txt']:(D/p.name).write_bytes(p.read_bytes())
archive=D/'own-runs-and-failures.tar.gz';members=[]
with tarfile.open(archive,'w:gz') as a:
 for p in sorted((O/'runs').glob('p131-*')):
  if p.is_file() and 'closure' not in p.name:a.add(p,arcname=p.name,recursive=False);members.append({'path':p.name,'SHA256':sha(p.read_bytes()),'bytes':p.stat().st_size})
with tarfile.open(archive,'r:gz') as a:
 for m in a.getmembers():assert sha(a.extractfile(m).read())==next(x['SHA256'] for x in members if x['path']==m.name)
(D/'archive-manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.131','archive':archive.name,'SHA256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,'members':members,'all_member_restore_match':True,'raw_reference':'research-data/ai-sigma/129-tactical-evaluation/runs-all-attempts.tar.gz','raw_archive_SHA256':'fc0b8cb2a85221bc61e5b4b30fd258d772cd88327dfff57337084c3a00be0a45','no_original_raw_copy':True},indent=2)+'\n')
print(json.dumps({'self_current0':len(ids),'archive_bytes':archive.stat().st_size,'member_count':len(members),'stopSHA':sha((D/'runtime-source-stopped-before-report.json').read_bytes())}))
