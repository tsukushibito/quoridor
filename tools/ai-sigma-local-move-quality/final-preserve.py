"""Finite result, source/runtime stop and restoration. No experiment launch."""
import json,hashlib,tarfile,subprocess,io,datetime,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];TOOL=Path(__file__).resolve().parent;OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-QUALITY';DATA=ROOT/'research-data/ai-sigma/134-local-move-quality'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();save=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
results=[read(p) for p in sorted(DATA.glob('quality134-group*-results.json'))];processes=[read(p) for p in sorted((OUT/'runs').glob('*.process.json'))];games=[g for r in results for g in r['games']];metrics=[m for r in results for m in r['metrics']]
assert len(games)==8 and len({g['id'] for g in games})==8
assert all(g['status']=='terminal' and g['reason']=='goal' and g['browser_replay']['final_key_exact'] and g['browser_replay']['history_exact'] for g in games)
assert all(m['classification']=='completed_legal' and m['postpublic_immutable'] for m in metrics)
assert sum(r['functional_public'] for r in results)==2
ids={}
for process in processes:
 assert not process['remaining'] and not process['unknown_adopted'] and process['exit']==0 and process['stop_reason'] is None
 for x in process['tracked']+[{'pid':process['runner_pid'],'start_ticks':process['runner_starttick']}]:ids[(x['pid'],x['start_ticks'])]={'pid':x['pid'],'start_ticks':x['start_ticks']}
live=[]
for x in ids.values():
 try:fields=(Path('/proc')/str(x['pid'])/'stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(fields[19])==x['start_ticks']:live.append(x)
assert not live
stops=[read(DATA/(r['run']+'-stop.json')) for r in results]
assert all(s['search_zero_all_rows'] and not s['current_same_identity'] and not s['remaining_unknown'] for s in stops)
seconds=lambda p:(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds()
resources={'managed_heavy_seconds':sum(seconds(p) for p in processes if p['phase']=='quality'),'managed_mock_seconds':sum(seconds(p) for p in processes if p['phase']=='protocol'),'heavy_budget_seconds':1800,'currentRSS_peak':max(p['peak_group_plus_runner_RSS'] for p in processes),'RAMguard_bytes':5905580032,'observed_storage_peak':max(p['peak_allocated_bytes'] for p in processes),'storage_guard_bytes':117440512,'affinity_violations':sum(len(p['affinity_violations']) for p in processes),'instant_peak_full_background_or_purekernel_CPU_not_proved':True}
source_after={str(p.relative_to(ROOT)):sha(p) for p in TOOL.iterdir() if p.is_file()};source_before_runs=[read(OUT/'runs'/(r['run']+'.inputs.json')) for r in results]
for record in source_before_runs:
 for path,digest in record['source'].items():assert sha(Path(path))==digest,'MEASURED_SOURCE_CHANGED'
bindings=[]
for r in results:
 b=read(OUT/'runs'/r['run']/'source-bindings.json')
 for item in b.values():assert sha(ROOT/item['path'])==item['original_SHA256']
 bindings.append({'run':r['run'],'source_Git':r['source_Git'],'served_adapted_hashes':{k:v['adapted_SHA256'] for k,v in b.items()}})
assert all(x['served_adapted_hashes']==bindings[0]['served_adapted_hashes'] for x in bindings)
necessary=[('models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx','d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'),('.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm','1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01')]
for path,digest in necessary:assert sha(ROOT/path)==digest
for path,digest in read(DATA/'intake.json')['132_final_data_refs'].items():assert sha(ROOT/'research-data/ai-sigma/132-deep-node-comparison'/path)==digest
readonly_paths=['tools/ai-sigma-deep-node-comparison/deep-input.js','tools/ai-sigma-actual-boundary-repair/reference-core.js','tools/ai-sigma-actual-boundary-repair/reference-control-run.js','tools/ai-sigma-actual-boundary-repair/host.js','tools/ai-sigma-cp-frame/numeric-browser.js','tools/ai-sigma-player-workers/player-control.cjs','tools/ai-sigma-cp-frame/shared-best-action.cjs']
for path in readonly_paths:necessary.append((path,sha(ROOT/path)))
stop={'issue':'quoridor-4lc.134','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_runtime_stopped':True,'source_after':source_after,'measured_source_hashes_unchanged':True,'bindings':bindings,'necessary_readonly_current_hashes':dict(necessary),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'recorded_identity_union':len(ids),'identities':list(ids.values()),'current_same_identity':live,'remaining_unknown':0,'Model2_drop_per_job':[{'run':s['run'],'drop':s['Model2_drop']} for s in stops],'all_searchACKzero':True,'main_timer_message_zero':True,'monitor_callbacks_waited':True,'inner_controlled_per_job':[{'run':s['run'],'remaining':s['inner_controlled']['remaining_pids'],'forced':s['inner_controlled']['forced'],'waited':s['inner_controlled']['waited']} for s in stops],'outer_sole_root_ownedwait':[{'run':p['name'],'remaining':p['remaining'],'unknown_adopted':p['unknown_adopted'],'kernel_boundary':p['kernel_boundary']} for p in processes],'resources':resources,'not_natural_termination_allperiod_or_allhost_proof':True}
save(DATA/'runtime-source-stopped-before-report.json',stop);save(OUT/'runtime-source-stopped-before-report.json',stop)
repeat=[]
raws={r['run']:read(OUT/'runs'/r['run']/'browser-result.json') for r in results}
for index in [3,4]:
 for branch in ['A','B']:
  selected=[(r,g) for r in results for g in r['games'] if g['input_index']==index and g['branch']==branch];assert len(selected)==2
  (r1,g1),(r2,g2)=selected;first=next((i for i,(a,b) in enumerate(zip(g1['actions'],g2['actions'])) if a!=b),None)
  obs=[]
  if first is not None:
   for r,g in selected:
    row=next(x for x in raws[r['run']]['rows'] if x['identity']['request_id']==g['turn_indices'][first]);obs.append({'rep':g['rep'],'Action':row['response']['body']['action'],'adopted_stats':row['adopted_stats'],'key':row['identity']['key'],'history':row['identity']['history']})
  repeat.append({'input_index':index,'branch':branch,'scores':[g['forced_side_score'] for r,g in selected],'new_publics':[g['new_public'] for r,g in selected],'totalplies':[g['total_ply'] for r,g in selected],'same_exact_continuation':g1['actions']==g2['actions'],'first_repeat_action_divergence_newply':first+1 if first is not None else None,'first_divergence_observations':obs,'sameinput_at_first_divergence':(obs[0]['key']==obs[1]['key'] and obs[0]['history']==obs[1]['history']) if obs else None})
public_classes={}
for m in metrics:public_classes[m['classification']]=public_classes.get(m['classification'],0)+1
final={'issue':'quoridor-4lc.134','planned_rollouts':8,'started_rollouts':8,'goal':8,'RuleA_200draw':0,'unfinished':0,'responsibility_loss':0,'NN_invalid':0,'unstarted':0,'connection_requested':2,'connection_completed_legal':2,'new_public':sum(r['new_public'] for r in results),'public_response_total':len(metrics),'public_classifications':public_classes,'hand_NN':sum(r['hand_NN'] for r in results),'startup_NN':sum(r['startup_NN'] for r in results),'model_session_count_per_job':2,'jobs':4,'startup6_per_job_separate':True,'selected_rollout_roots':sum(bool(m['spec'].get('numeric_selected')) and not m['spec'].get('functional') for m in metrics),'connection_roots':2,'root_numeric_gates':all(m['numeric_gate'].get('NN137_finite_strict') for m in metrics if m['spec'].get('numeric_selected')),'fixed_golden_newroots':False,'games':games,'repeat_comparison':repeat,'first_action_branch_is_K32_not_T500_candidate':True,'max_public_ms':max(m['public_ms'] for m in metrics),'adopt_planned_ms':411,'opposite_t0_before_old_ACK_observed':sum(bool(m['opposite_previous'] and m['opposite_previous']['input_before_old_ACK']) for m in metrics),'public_before_ACK':sum(bool(m['public_before_ACK']) for m in metrics),'post_public_newNN_definite':sum(m['post_public_newNN_definite'] for m in metrics),'post_cutoff_newNN_definite':sum(m['post_cutoff_newNN_definite'] for m in metrics),'discarded_returns':sum(m['discarded_returns'] for m in metrics),'worker_stop_after_D_observed':sum(m['worker_stop_class']=='lower_gt_D' for m in metrics),'resources':resources,'source_bindings':bindings,'root_CP_missing_features_modelCPU_exactAtomicstore_intermediateDrift_not_filled':True,'conclusion':'Input3: forced candidate K32 Action scores1/1 versus reference0/0. Input4: both0/0. No consistent candidate-only bad move support. Keep policies; reference distribution similarity is not an improvement criterion. Stop repeating this local scale. Different continuations/finish lengths under the same score show finite scheduling sensitivity, not a model/value cause. General strength,119 causal loss,C/FPU effect,NI/oracle are unrecognized.','next_decision':'No automatic C/FPU or preparation change. Any next allocation must reconsider the input/quality scale separately; this fixed-policy continuation does not identify a model/value defect.','additional_rollouts':0,'formalNI_Sigma_actualgo':False,'old_results_integrated':False}
save(DATA/'final-results.json',final)
failures=[read(p) for p in sorted((OUT/'runs').glob('*.admission-failure.json'))]
save(DATA/'failures-and-unexecuted.json',{'static_first_schema_failure':read(OUT/'mock-failure-r1.json'),'admission_failures':failures,'all_admission_failures_child_started_false':all(not x['child_started'] for x in failures),'scientific_rollouts_retried':0,'scientific_unstarted':0,'late_firstnone_fault_loss_invalid_infra':0,'source_tree_copy_removed_beforeNN':True,'original_preregister_SHA':'a3b368a42a3d0efdbac8eb085f4c12db7c10de5e55f31ec9891ddec8de666a38','executed_minimal_preregister_SHA':sha(DATA/'preregister.json')})
archive_checks=[]
for p in sorted(DATA.glob('quality134-group*-archive-manifest.json')):
 m=read(p);assert sha(ROOT/m['archive'])==m['SHA256']
 with tarfile.open(ROOT/m['archive']) as t:
  for x in m['members']:assert hashlib.sha256(t.extractfile(x['path']).read()).hexdigest()==x['SHA256']
 archive_checks.append({'archive':m['archive'],'SHA256':m['SHA256'],'members':len(m['members']),'stream_restore':True})
save(DATA/'archive-restore-index.json',archive_checks)
# Intake/config/failure receipts and source-stop in a separate small archive; no duplicated model or raw game results.
files=[p for p in OUT.iterdir() if p.is_file() and 'private-index' not in p.name]
files+=[p for p in (OUT/'runs').iterdir() if p.is_file() and (p.name.startswith('quality134-mock') or 'admission-failure' in p.name or p.name.startswith(('quality134-group1-r1.','quality134-group1-r2.')))]
members=[{'path':str(p.relative_to(OUT)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(files))]
archive=DATA/'intake-failures-stop.tar.gz'
with tarfile.open(archive,'w:gz') as t:
 for m in members:t.add(OUT/m['path'],arcname=m['path'],recursive=False)
with tarfile.open(archive) as t:
 for m in members:assert hashlib.sha256(t.extractfile(m['path']).read()).hexdigest()==m['SHA256']
save(DATA/'intake-failures-manifest.json',{'archive':str(archive.relative_to(ROOT)),'SHA256':sha(archive),'members':members,'stream_restore':True})
def allocated(folder):return sum(p.stat().st_blocks*512 for p in folder.rglob('*') if p.is_file())
storage={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'self_source_current':allocated(TOOL),'self_runtime_current':allocated(OUT),'self_data_current':allocated(DATA),'self_allocation_bytes':134217728,'self_guard_bytes':117440512,'reservation_within_existing_experiment_entry_bytes':2147483648,'parent_reservation_increase':0,'unused_self_reservation_before_Git':134217728-allocated(TOOL)-allocated(OUT)-allocated(DATA),'old_retained_and_unverified_entry_usage_not_decreased':True,'past_peak_not_added_to_current':True,'shared_Git_increment_not_yet_byte_attributed':True,'no_shared_original_raw_or_model_deleted':True}
assert storage['self_source_current']+storage['self_runtime_current']+storage['self_data_current']<storage['self_guard_bytes'];save(DATA/'storage-current.json',storage)
print(json.dumps({'goal':8,'new_public':final['new_public'],'hand_NN':final['hand_NN'],'startup_NN':final['startup_NN'],'identities':len(ids),'stop_SHA':sha(DATA/'runtime-source-stopped-before-report.json'),'resources':resources,'storage':storage}))
