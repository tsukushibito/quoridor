import pathlib,json,datetime,hashlib,tarfile
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-INDEPENDENT';T=R/'tools/ai-sigma-local-move-independent';D=R/'research-data/ai-sigma/135-local-move-independent';H=lambda b:hashlib.sha256(b).hexdigest();jobs=[];ids=set()
for p in (O/'runs').glob('p135-*.process.json'):
 x=json.loads(p.read_text());jobs.append({k:x[k] for k in ['name','start','end','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','remaining','unknown_adopted','all_observed_TIDs_at_assigned_CPU','kernel_adoptions']})
 for q in x['tracked']+[{'pid':x['runner_pid'],'start_ticks':x['runner_starttick']}]:ids.add((q['pid'],q['start_ticks']))
live=[]
for p,t in ids:
 try:s=pathlib.Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(s[19])==t:live.append({'pid':p,'starttick':t})
assert not live and all(not j['remaining'] and not j['unknown_adopted'] for j in jobs)
initial=json.loads((O/'input-before.json').read_text());final=json.loads((O/'final-input-binding.json').read_text());after=[]
for c in final['scientific_archive_required_inputs_unchanged']+final['checks']:
 p=R/c['path'];assert H(p.read_bytes())==c['SHA256'];after.append({'path':c['path'],'SHA256':c['SHA256']})
(O/'input-after.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'required_currentmatch':after,'readonly_upstream':True},indent=2)+'\n')
(O/'failures.json').write_text(json.dumps({'initial_preregister_hash_assumption_failure':'original a3b... vs executed355d...; original recovered by Git9c8224a, only nonrootCP tree removal and annotation, science plan unchanged','browser_adapter_generation_error':'ValueError substring not found during template generation','managed_r1':'Node missing browser.cjs, exit1 before Chrome; after successful launch admission, noNN/model/game','fixed_r2':'saved replay pass; no upstream modification','original134_admission2_failures_spawn0':True,'original134_static_schema_failure_preserved':True,'original_packed_Git_attribution_failure_not_science_failure':final['owner_packed_Git_charge_failure_preserved'],'scope_tmp_note':'initial three Beads read files staged briefly /tmp then moved into owner artifact; no other scope changed','false_NN_mismatch_or_loss0':True,'successful_run_selection0':True},indent=2)+'\n')
run=O/'runs/p135-saved-r2';stop={'issue':'quoridor-4lc.135','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'jobs':jobs,'identity_count':len(ids),'current_same_identity':live,'currentabsence_not_natural_allperiod':True,'source_write_stopped':True,'source_hashes':{str(p.relative_to(R)):H(p.read_bytes()) for p in T.iterdir() if p.is_file()},'browser_stop':json.loads((run/'browser-stop.json').read_text()),'monitor_callback_stop':json.loads((run/'pause-monitor-stop.json').read_text()),'NN':0,'new_Model_sessions':0,'new_AI_Workers':0,'new_search_game_holdout':0,'input_hashafter':len(after),'outer_remaining_unknown0':True,'unmanaged_short_intake_prepare_closure_PID_RSS_missing':True,'original134_Model2_search_main_monitor_receipts':'input-before.source_and_stop plus final-source stop refs; four jobs forced grace is separate from outerwait/current0'}
(D/'runtime-source-stopped-before-report.json').write_text(json.dumps(stop,indent=2)+'\n')
for n in ['config.json','config-r2.json','static-config.json','input-before.json','input-after.json','preregister-binding.json','final-input-binding.json','source-audit.json','failures.json']:(D/n).write_bytes((O/n).read_bytes())
for n in ['all-independent','independent-typed','browser-summary','finally']:(D/(n+'.json')).write_bytes((run/(n+'.json')).read_bytes())
a=D/'own-runs-and-failures.tar.gz';members=[]
with tarfile.open(a,'w:gz') as t:
 for p in sorted((O/'runs').rglob('*')):
  if not p.is_file() or '/t/' in str(p) or '/xdg-' in str(p):continue
  n=str(p.relative_to(O));b=p.read_bytes();t.add(p,arcname=n,recursive=False);members.append({'path':n,'SHA256':H(b),'bytes':len(b)})
with tarfile.open(a) as t:
 for m in t.getmembers():assert H(t.extractfile(m).read())==next(x['SHA256'] for x in members if x['path']==m.name)
(D/'archive-manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.135','archive':a.name,'SHA256':H(a.read_bytes()),'bytes':a.stat().st_size,'members':members,'all_member_restore_match':True,'original4archive_reference':final['scientific_archive_required_inputs_unchanged'],'original_raw_copy_saved0':True},indent=2)+'\n')
p=O/'saved-input.json';clean={'path':str(p.relative_to(R)),'SHA256':H(p.read_bytes()),'bytes':p.stat().st_size,'removed_after_own_browser_reader_stop':True,'regenerate':'prepare.py from original fixed4archives and necessary member hashes; original not modified'};p.unlink();(D/'own-unused-expansion-cleanup.json').write_text(json.dumps(clean,indent=2)+'\n')
print(json.dumps({'own_identity_current0':len(ids),'jobs':jobs,'archive':{'SHA':H(a.read_bytes()),'bytes':a.stat().st_size,'members':len(members)},'stopSHA':H((D/'runtime-source-stopped-before-report.json').read_bytes())}))
