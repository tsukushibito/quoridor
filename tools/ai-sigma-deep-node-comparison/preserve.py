"""Freeze bounded deep findings, source binding and controlled recovery without NN."""
from pathlib import Path
import datetime,hashlib,json,tarfile,subprocess
ROOT=Path(__file__).resolve().parents[2];TOOL=Path(__file__).parent
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/DEEP-NODE-COMPARISON'
DATA=ROOT/'research-data/ai-sigma/132-deep-node-comparison';RUN=OUT/'runs/deep132-measure-r1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
raw=read(RUN/'browser-result.json');assert len(raw['deep_results'])==12 and not raw['errors']
assert raw['completed_primary']==8 and len(raw['parity'])==2
for r in raw['deep_results']:
    assert not r['primary'] and not r.get('main_gate_error') and not r['zero']['handles'] and not r['zero']['activeNN']
    assert r['rootN']==r['completed_backups']==r['spec']['K'] and r['edge_sum']==r['spec']['K']-1
    if r['spec']['instrumented']:assert len(r['trace'])==8
processes=[read(p) for p in (OUT/'runs').glob('*.process.json')]
identities={}
for p in processes:
    assert p['exit']==0 and not p['remaining'] and not p['stop_reason'] and not p['unknown_adopted']
    for identity in p['tracked']+[{'pid':p['runner_pid'],'start_ticks':p['runner_starttick']}]:identities[identity['pid'],identity['start_ticks']]=identity
live=[]
for pid,tick in identities:
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        if int(fields[19])==tick:live.append({'pid':pid,'start_ticks':tick})
    except FileNotFoundError:pass
assert not live
seconds=lambda p:(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds()
resources={phase:sum(seconds(p) for p in processes if p['phase']==phase) for phase in ['build','count','protocol']}
resources.update({'observed_currentRSS_peak':max(p['peak_group_plus_runner_RSS'] for p in processes),'instant_peak_background_CPU_metadata_missing':True,'currentRSS_not_ru_maxrss':True,'observed_runtime_storage_peak_excludes_private_build_in_nonbuild_phase':True,'full_current_allocated_bytes':sum(p.stat().st_blocks*512 for folder in [OUT,TOOL,DATA] for p in folder.rglob('*') if p.is_file())})
assert resources['build']<=600 and resources['count']<=600 and resources['build']+resources['count']<=1200 and resources['full_current_allocated_bytes']<469762048
models=read(RUN/'finally-model-drop.json');timer=read(RUN/'main-timers-stop.json');monitor=read(RUN/'pause-monitor-stop.json');controlled=read(RUN/'outer-controlled-stop.json')
assert models['handles']==models['activeNN']==0 and len(models['players'])==2
assert not timer['main_timers'] and not timer['pending_messages']
assert monitor['all_owned_read_callbacks_waited'] and not monitor['pending_children'] and not monitor['active_monitor_timer']
assert controlled['remaining_pids']==0 and controlled['waited'] and controlled['zombie_identities_absent']
source_after={str(p.relative_to(ROOT)):sha(p) for p in TOOL.rglob('*') if p.is_file()}
stop={'issue':'quoridor-4lc.132','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_runtime_stopped':True,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'identities':list(identities.values()),'recorded_identity_union':len(identities),'current_same_identity':live,'current_absence_not_natural_or_all_period_proof':True,'Model2_drop':models,'main_timer_message_zero':timer,'monitor_callbacks_all_waited':True,'inner_controlled':{'forced':controlled['forced'],'remaining':0,'waited':controlled['waited']},'outer_owned_wait':[{'run':p['name'],'phase':p['phase'],'remaining':p['remaining'],'unknown_adopted':p['unknown_adopted'],'kernel_adoptions':p['kernel_adoptions']} for p in processes],'resources':resources,'source_after':source_after}
save(DATA/'runtime-source-stopped-before-report.json',stop);save(OUT/'runtime-source-stopped-before-report.json',stop)
rows=[]
for r in raw['deep_results']:
    rows.append({'spec':r['spec'],'id':r['id'],'Action':r['cp']['action'],'completed_backup':r['completed_backups'],'rootN':r['rootN'],'edge_sum':r['edge_sum'],'NN_calls':r['NN_calls'],'terminal_noNN':r['terminal_noNN_backups'],'wrapper_ms':r['wrapper_end_ms']-r['wrapper_start_ms'],'first_CP_ms_from_wrapper':r['first_CP_ms']-r['wrapper_start_ms'],'first_API_await_ms':r['spans'][0]['API_end_ms']-r['spans'][0]['API_start_ms'],'root_prepare_internal_missing':True,'max_depth_candidate':r['cp'].get('max_depth') if r['engine']=='candidate' else None,'reference_depth_missing':True,'cap_candidate':r['cp'].get('cap') if r['engine']=='candidate' else None,'reference_uncapped':r['engine']=='reference','zero':r['zero'],'gate':r['gate'],'selected_trace_nodes':len(r['trace'] or []),'NN_discard':0,'NN_discard_basis':'each infer result immediately resumed/backup; all calls completed, zero residual; not game retirement','candidate_parentQ_valueSum_missing':r['engine']=='candidate'})
shared=[n for c in raw['comparisons'] for n in c['deep']['shared']]
assert len(shared)==13 and all(n['history_exact'] and n['features_exact'] and n['leaf_turn_equal'] and n['path_Action_equal'] and n['numeric']['mixed'] and n['leaf_value']['mixed'] and n['backup_sign_candidate'] and n['backup_sign_reference'] for n in shared)
result={'issue':'quoridor-4lc.132','run':'deep132-measure-r1','measured_source_Git':read(RUN/'config.json')['Git'],'started_parity':4,'completed_parity':4,'parity_backup':32,'parity_NN':32,'started_primary':8,'completed_primary':8,'primary_backup':256,'primary_NN':256,'startup_NN':read(RUN/'startup.json')['startup_NN'],'terminal_noNN_primary':0,'unexecuted_primary':0,'numerical_failures':0,'input_failures':0,'trace_failures':0,'raw_summary_started_search_requests0_invalid_mapping':True,'actual_counts_from_explicit_phase_fields':True,'rows':rows,'parity':raw['parity'],'comparisons':raw['comparisons'],'shared_roots':4,'shared_nonroot':9,'selected_primary_nodes_per_engine':32,'unshared_primary_nodes_per_engine':19,'root_NN_exact':True,'shared_deep_NN_exact':True,'terminal_actual_all_nonterminal':True,'terminal_noNN_branch_not_exercised_primary':True,'finite_backup_sign_supported':True,'full_deep_general_equivalence':False,'mid_input_fixedgolden_NN_reference':False,'start_clock':read(RUN/'startup.json')['worker_clocks'],'end_clock':read(RUN/'clock-end.json'),'intermediate_drift_exactAtomicstore_kernelCPU_missing':True,'measurement_overhead_uncalibrated_single_K8_only':True,'resources':resources,'decision':'Same evaluated shared states, different Action on inputs3/4; rule bundle attribution unresolved. Keep policy, no C/FPU adoption. One next proposal: conditional 130P2 local hand-quality comparison on these two fixed positions, separately allocated; no rollout here.','next_proposal_max1':'130P2: force A or B selected first Action on input3/4 then fixedSigma continuation, preregister all branches; policy-dependent diagnostic, not true-quality oracle.','remaining_limits':['unshared 19 selected states per engine; no all-tree claim','all primary traces nonterminal; actual terminal backup coverage absent','candidate node valueSum/parentQ absent','reference final root Q vs candidate root NN are different conventions','single finite K8 parity timing cannot estimate pure trace overhead','A/B are multiple search-rule bundles; C/FPU single-cause unproven'],'games':0,'P2_rollout_started':0,'formalNI_Sigma_actual_go':False}
save(DATA/'final-results.json',result)
# Required files only: no dependency/model/full target copies.
files=sorted(p for p in OUT.rglob('*') if p.is_file() and not any(x in ['t','xdg-cache','xdg-config','target','target-baseline','target-trace'] for x in p.relative_to(OUT).parts) and 'private-index' not in p.name)
members=[{'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'SHA256':sha(p)} for p in files]
archive=DATA/'all-attempts.tar.gz'
with tarfile.open(archive,'w:gz') as t:
    for p in files:t.add(p,arcname=str(p.relative_to(OUT)),recursive=False)
with tarfile.open(archive) as t:
    for m in members:assert hashlib.sha256(t.extractfile(m['path']).read()).hexdigest()==m['SHA256']
save(DATA/'archive-manifest.json',{'issue':'quoridor-4lc.132','archive_SHA256':sha(archive),'members':members,'stream_restore_all_SHA':True,'restore_relative_to':str(OUT.relative_to(ROOT)),'measured_source_Git':result['measured_source_Git'],'build_target_not_archived':True,'binaries_included':['build/baseline.wasm','build/trace.wasm'],'model_shared_reference':True})
print(json.dumps({'stop_SHA':sha(DATA/'runtime-source-stopped-before-report.json'),'archive_SHA':sha(archive),'members':len(members),'identity_union':len(identities),'resources':resources,'shared_nonroot':9,'different_Action_inputs':[3,4]}))
