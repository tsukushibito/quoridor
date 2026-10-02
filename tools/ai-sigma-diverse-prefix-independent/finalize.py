from pathlib import Path
import json,datetime,hashlib,tarfile,os
R=Path(__file__).resolve().parents[2];T=R/'tools/ai-sigma-diverse-prefix-independent';O=R/'.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX-INDEPENDENT';D=R/'research-data/ai-sigma/122-diverse-prefix-independent';H=lambda b:hashlib.sha256(b).hexdigest();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=json.loads((O/'input-after.json').read_text())['checks'];assert all(H((R/p).read_bytes())==h for p,h in checks.items())
identity={};jobs=[]
for p in (O/'runs').glob('p122-*.process.json'):
 j=json.loads(p.read_text());assert not j['remaining'] and not j['unknown_adopted'];jobs.append({k:j[k] for k in ['name','phase','start','end','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','assigned_CPU','all_observed_TIDs_at_assigned_CPU']})
 for q in j['tracked']+[{'pid':j['runner_pid'],'start_ticks':j['runner_starttick']}]:identity[int(q['pid']),int(q.get('start_ticks',q.get('starttick')))]=q
for p in (O/'runs').glob('p122-*/browser-stop.json'):
 j=json.loads(p.read_text());assert j['remaining_pids']==0 and j['waited'];
 for q in j['tracked']:identity[int(q['pid']),int(q['starttick'])]=q
live=[]
for pid,tick in identity:
 try:
  z=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
  if int(z[19])==tick:live.append({'pid':pid,'start_ticks':tick})
 except FileNotFoundError:pass
assert not live
source={str(p.relative_to(R)):H(p.read_bytes()) for p in T.iterdir() if p.is_file()};stop={'issue':'quoridor-4lc.122','UTC':now,'source_runtime_stopped':True,'new_NN_model_load_games':0,'jobs':jobs,'recorded_identity_count':len(identity),'current_same_identity':live,'browser_forced_outer_waited':'each runs/*/browser-stop.json and *.process.json','Modeldrop_required':False,'reason':'analysis-only browser created no Model/session/Worker; original119 both real Modeldrops verified independently','monitor_callbacks_waited':True,'unknown_signal_wait':0,'source_after':source,'input_after_count':len(checks),'afterjob_metadata_not_managed_runtime':True,'currentabsence_not_natural_or_allperiod':True}
(O/'runtime-source-stopped-before-report.json').write_text(json.dumps(stop,indent=2));D.mkdir(exist_ok=True)
for n,p in [('independent-results.json',O/'runs/p122-summary-r2/all-independent.json'),('prefix-independent.json',O/'runs/p122-saved-r1/prefix-independent.json'),('input-reference-manifest.json',O/'input-after.json'),('runtime-source-stopped-before-report.json',O/'runtime-source-stopped-before-report.json'),('selection-preregister.json',O/'selection-preregister.json'),('identity-denominator-difference.json',O/'identity-denominator-difference.json')]:
 (D/n).write_bytes(p.read_bytes())
# Preserve only compact evidence. No upstream raw duplication; own one-pair expansion already removed.
current=os.environ.get('SIGMA_DUMMY_RUN_ID','');files=[]
for p in O.rglob('*'):
 if p.is_file() and not any(v in ['t','xdg-cache','xdg-config'] for v in p.relative_to(O).parts) and 'private-index' not in p.name and not (current and current in str(p.relative_to(O))):files.append(p)
archive=D/'run-evidence.tar.gz';members=[{'path':str(p.relative_to(O)),'SHA256':H(p.read_bytes()),'bytes':p.stat().st_size} for p in files]
with tarfile.open(archive,'w:gz') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(O)),recursive=False)
with tarfile.open(archive) as t:
 for x in members:assert H(t.extractfile(x['path']).read())==x['SHA256']
manifest={'issue':'quoridor-4lc.122','archive':'run-evidence.tar.gz','SHA256':H(archive.read_bytes()),'bytes':archive.stat().st_size,'members':members,'all_members_stream_restore_checked':True,'input_archives_read_only_reference':True,'excluded_current_closure_process':current,'restore_root':str(O.relative_to(R))};(D/'archive-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'archive_SHA':manifest['SHA256'],'archive_bytes':manifest['bytes'],'members':len(members),'stop_SHA':H((D/'runtime-source-stopped-before-report.json').read_bytes()),'self_identity_current0':len(identity),'self_resources':jobs}))
