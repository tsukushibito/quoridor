import json,pathlib,hashlib,tarfile,datetime,os
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/142-wallless-oracle';O=R/'.artifacts/ai-sigma/resume-20261002/WALLLESS-ORACLE';RUNS=O/'runs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for i in range(2):
 run=RUNS/'p142-oracle-r2';g=json.loads((run/f'generation-{i}.json').read_text());l=json.loads((run/f'label-{i}.json').read_text());check=json.loads((run/f'certificate-check-{i}.json').read_text());short={k:v for k,v in l.items() if k!='proof'}
 results.append({'id':g['case'],'attempts':len(g['attempts']),'all_attempt_errors':[a['error'] for a in g['attempts']],'adopted_depth':g['adopted']['depth'],'pawns':g['adopted']['pawns'],'side':g['adopted']['side'],'key':g['adopted']['key'],'walls':g['adopted']['walls'],'prefix_length':len(g['adopted']['prefix']),'features_count':len(g['adopted']['featuresbits']),'labels':short,'certificate_check':check,'generated_sha256':sha(run/f'generation-{i}.json'),'full_label_sha256':sha(run/f'label-{i}.json')})
(D/'finite-results.json').write_text(json.dumps({'issue':'quoridor-4lc.142','scientific_run':'p142-oracle-r2','tested_source':'3866532','preregister_SHA256':sha(D/'preregister.json'),'results':results,'all_attempts':2,'unexecuted_attempt_slots':6,'NN':0,'AI_quality_evaluated':False,'no_scientific_repetition':True,'independent_rule_implementation':False},indent=2)+'\n')
files=sorted(p for p in RUNS.rglob('*') if p.is_file() and not any(part in ['t','xdg-cache','xdg-config'] for part in p.relative_to(RUNS).parts));members=[]
with tarfile.open(D/'runs.tar.gz','w:gz',compresslevel=6) as t:
 for p in files:
  name=str(p.relative_to(RUNS));t.add(p,arcname=name,recursive=False);members.append({'name':name,'bytes':p.stat().st_size,'sha256':sha(p)})
with tarfile.open(D/'runs.tar.gz','r:gz') as t:
 actual={x.name:x for x in t.getmembers()};assert set(actual)=={x['name'] for x in members}
 for m in members:
  b=t.extractfile(m['name']).read();assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256']
(D/'archive-manifest.json').write_text(json.dumps({'archive':'runs.tar.gz','sha256':sha(D/'runs.tar.gz'),'members':members,'stream_restore_verified':True,'excluded':'regenerable Chromium temp/cache; no scientific proof/log excluded'},indent=2)+'\n')
jobs=[json.loads(p.read_text()) for p in RUNS.glob('*.process.json')]
served=json.loads((RUNS/'p142-oracle-r2/actual-served-source.json').read_text());binding=[]
for idx,s in enumerate(served['sources']):
 p=R/s['path'];binding.append({**s,'current_sha256':sha(p),'browser_echo_SHA256':served['browser_script_sha256'][idx+1],'unchanged':sha(p)==s['sha256']==served['browser_script_sha256'][idx+1]})
assert all(x['unchanged'] for x in binding)
source_before=json.loads((RUNS/'p142-oracle-r2.inputs.json').read_text())['source'];source_after={p:sha(pathlib.Path(p)) for p in source_before};assert source_before==source_after
own_alloc=sum(p.stat().st_blocks*512 for d in [R/'tools/ai-sigma-wallless-oracle',D,O] for p in d.rglob('*') if p.is_file())
# New Git data conservatively counted again at uncompressed content size, not claimed actual pack increment.
git_upper=sum(p.stat().st_size+1024 for d in [R/'tools/ai-sigma-wallless-oracle',D] for p in d.rglob('*') if p.is_file())+65536
resource={'old_conservative_held':8908800,'own_current_allocated':own_alloc,'new_git_content_upper_estimate':git_upper,'remaining_report_handoff_forecast':131072,'combined_forecast':8908800+own_alloc+git_upper+131072,'combined_guard':14680064,'reservation':16777216,'additional_reservation':0,'new_scope_target':2097152,'source_input_binding':binding,'self_source_before_after_equal':True,'jobs':[{k:j[k] for k in ['name','start','end','exit','stop_reason','assigned_CPU','peak_group_plus_runner_RSS','peak_allocated_bytes','remaining','unknown_adopted','instant_peak_not_guaranteed','all_observed_TIDs_at_assigned_CPU']} for j in jobs],'browser_wall_total':sum((datetime.datetime.fromisoformat(j['end'])-datetime.datetime.fromisoformat(j['start'])).total_seconds() for j in jobs if j['phase']=='oracle'),'static_supervised_wall_total':sum((datetime.datetime.fromisoformat(j['end'])-datetime.datetime.fromisoformat(j['start'])).total_seconds() for j in jobs if j['phase']=='protocol'),'unmonitored_short_management_commands':'initial reads/claim/writes/Git/report commands not full-period RSS/CPU proof; exact aggregate command wall unavailable','old_unknown_not_decreased':True,'global_storage_reaudit':False}
assert resource['combined_forecast']<resource['combined_guard']
(D/'resource-and-binding.json').write_text(json.dumps(resource,indent=2)+'\n')
print(json.dumps({'archive_bytes':(D/'runs.tar.gz').stat().st_size,'archive_members':len(members),'resource':{k:v for k,v in resource.items() if k not in ['source_input_binding','jobs']}}))
