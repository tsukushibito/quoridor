"""Preserve stopped tactical rows and bounded claims; never execute NN."""
import datetime
import hashlib
import json
import statistics
import tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'.artifacts/ai-sigma/resume-20261002/TACTICAL-EVALUATION'
DATA = ROOT/'research-data/ai-sigma/129-tactical-evaluation'
RUN = OUT/'runs/tactical129-measure-r1'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
raw = read(RUN/'browser-result.json')
assert len(raw['rows']) == 12 and not raw['errors']
drop = read(RUN/'finally-model-drop.json')
timer = read(RUN/'main-timers-stop.json')
monitor = read(RUN/'pause-monitor-stop.json')
controlled = read(RUN/'outer-controlled-stop.json')
assert drop['handles'] == drop['activeNN'] == 0 and len(drop['players']) == 2
assert timer['main_timers'] == 0 and not timer['pending_messages']
assert monitor['all_owned_read_callbacks_waited'] and not monitor['pending_children'] and not monitor['active_monitor_timer']
assert controlled['remaining_pids'] == 0 and controlled['waited'] and controlled['zombie_identities_absent']
processes = [read(p) for p in (OUT/'runs').glob('*.process.json')]
identities = {}
for process in processes:
    assert process['exit'] == 0 and not process['stop_reason'] and not process['remaining'] and not process['unknown_adopted']
    for identity in process['tracked'] + [{'pid':process['runner_pid'], 'start_ticks':process['runner_starttick']}]:
        identities[identity['pid'], identity['start_ticks']] = identity
live = []
for pid, tick in identities:
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) == tick: live.append({'pid':pid, 'start_ticks':tick})
    except FileNotFoundError: pass
assert not live
seconds = lambda p: (datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds()
resources = {'managed_heavy_seconds':sum(seconds(p) for p in processes if p['phase']!='protocol'), 'managed_static_seconds':sum(seconds(p) for p in processes if p['phase']=='protocol'), 'currentRSS_peak':max(p['peak_group_plus_runner_RSS'] for p in processes), 'observed_storage_peak':max(p['peak_allocated_bytes'] for p in processes), 'observed_affinity_violations':sum(len(p.get('affinity_violations', [])) for p in processes), 'currentRSS_not_ru_maxrss':True, 'instant_peak_background_CPU_short_metadata_unobserved':True}
stop = {'issue':'quoridor-4lc.129', 'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_runtime_stopped':True, 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'identities':list(identities.values()), 'recorded_identity_union':len(identities), 'current_same_identity':live, 'remaining_unknown':0, 'Model2_drop_zero':drop, 'main_timer_message_zero':timer, 'monitor_callbacks_waited':True, 'inner_controlled':{'remaining':0,'forced':controlled['forced'],'waited':controlled['waited']}, 'outer_owned_wait':[{'run':p['name'],'remaining':p['remaining'],'unknown_adopted':p['unknown_adopted'],'kernel_adoptions':p['kernel_adoptions']} for p in processes], 'resources':resources, 'source_after':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'tools/ai-sigma-tactical-evaluation').iterdir() if p.is_file()}, 'current_absence_not_natural_or_all_period_proof':True}
save(OUT/'runtime-source-stopped-before-report.json', stop)
save(DATA/'runtime-source-stopped-before-report.json', stop)
metrics = []
for row in raw['rows']:
    clock, response, diagnostic = row['worker_clock'], row['response'], row['diagnostic']
    adopted = row['adopted_stats']
    assert adopted and response['classification']=='completed_legal' and row['postpublic_immutable']
    assert row['tactical_verdict']['classification']=='pass'
    assert adopted['edge_sum']==adopted['completed_backup']-1
    assert adopted['sequence']==response['body']['sequence']
    assert adopted['terminal_noNN_backup']==adopted['completed_backup']-adopted['cp_NN_calls']
    nn = diagnostic['NN_control_events']
    first = diagnostic['sab_publications'][0]
    first_api = nn[0]
    t0, stamp = row['identity']['t0_ms'], response['stamp_ms']
    def interval(t):
        return {'lower_ms':t-clock['hi_ms']-t0,'upper_ms':t-clock['lo_ms']-t0}
    if row['spec']['condition']=='S':
        assert adopted['completed_backup']==adopted['cp_NN_calls']==row['hand_NN']==1
        assert len(diagnostic['sab_publications'])==1 and not any(n['result_discarded'] for n in nn)
    metrics.append({'spec':row['spec'],'request_id':row['identity']['request_id'],
        'Action':response['body']['action'],'tactical_verdict':row['tactical_verdict'],
        'generation':row['identity']['generation'],'adopted_stats':adopted,
        'first_CP_validation_interval':interval(first['validation_end_ms']),
        'first_publication_begin_interval':interval(first['begin_ms']),
        'request_to_first_API_start_interval':interval(first_api['session_run_start_ms']),
        'first_infer_wrapper_start_interval':interval(first_api['start_ms']),
        'first_API_await_ms':first_api['session_run_end_ms']-first_api['session_run_start_ms'],
        'root_internal_preparation_span_missing':True,
        'adopt_planned_ms':row['identity']['seal_ms']-t0,'adopt_timer_ms':response['timer_ms']-t0,
        'adopt_stamp_ms':stamp-t0,'adopt_sequence':response['body']['sequence'],
        'hand_NN':row['hand_NN'],'result_discarded_marker_count':sum(n['result_discarded'] for n in nn),
        'hand_NN_minus_adopt_CP_NN':row['hand_NN']-adopted['cp_NN_calls'],
        'private_result_error':diagnostic['result'].get('error'),
        'public_before_ACK':stamp<row['stop']['main_received_ms'],
        'post_public_new_NN_definite':row['post_public_NN_definite'],
        'self_wait':row['own_previous_wait'],'worker_stop_class':row['worker_stop_class'],
        'ACK_wall_ms':row['ACK_wall_ms'],'stop_to_ACK_interval':row['stop_to_main_ACK_interval'],
        'dynamic_self_gate':row['gate'],'public_causes':response['causes'],
        'exact_Atomicstore_kernel_CPU_missing':True})
normal=[r for r in metrics if r['spec']['condition']!='S']
stress=[r for r in metrics if r['spec']['condition']=='S']
assert len(normal)==8 and len(stress)==4
result = {'issue':'quoridor-4lc.129','source_Git':'766605299347c46869a2154afe27412162917d2f',
    'run':'tactical129-measure-r1','planned':12,'started':raw['started'],
    'completed_legal':12,'normal_pass':8,'stress_pass':4,'certified_legal_blunder':0,
    'late':0,'firstnone':0,'enginefault':0,'infraunfinished':0,'unexecuted':0,
    'hand_NN':sum(r['hand_NN'] for r in metrics),'startup_NN':read(RUN/'startup.json')['startup_NN'],
    'normal_adopt_backup':sum(r['adopted_stats']['completed_backup'] for r in normal),
    'normal_adopt_CP_NN':sum(r['adopted_stats']['cp_NN_calls'] for r in normal),
    'normal_terminal_noNN_backup':sum(r['adopted_stats']['terminal_noNN_backup'] for r in normal),
    'stress_adopt_backup':4,'stress_NN':4,
    'private_retired_STALE_GENERATION_rows':sum(r['private_result_error']=='STALE_GENERATION' for r in metrics),
    'private_retirement_not_public_engine_fault':True,
    'explicit_result_discarded_markers':sum(r['result_discarded_marker_count'] for r in metrics),
    'NN_beyond_adopt_CP':sum(r['hand_NN_minus_adopt_CP_NN'] for r in metrics),
    'postpublic_newNN_definite':sum(r['post_public_new_NN_definite'] for r in metrics),
    'normal_public_before_ACK':sum(r['public_before_ACK'] for r in normal),
    'max_public_ms':max(r['adopt_stamp_ms'] for r in metrics),
    'startup_model_init_separate':read(RUN/'model-load.json'),'metrics':metrics,
    'root_pairs':raw['root_pairs'],'normal_numeric_roots':8,'fixed_prefix_NN_reference':False,
    'golden_startup_references':6,'tactical_contexts_all_P1':True,
    'label_preflight_before_model_load':read(RUN/'label-input-check.json'),
    'labels_sharedRuleA_depth2_node20000_finite':True,
    'clock_start':read(RUN/'startup.json')['worker_clocks'],'clock_end':read(RUN/'clock-end.json'),
    'intermediate_drift_missing':True,'candidate_parentQ_missing':True,
    'APIawait_not_kernel_CPU':True,'same_backup_not_same_NN_CPU':True,
    'isolated_all_workers_zero_between_requests':True,'real_game_opponent_t0_policy_unchanged':True,
    'resources':resources,'conclusion':'All normal policies and root1 stress pass these finite labels. Stop narrow-label expansion/repetition; keep policy and propose a distinct deeper/strategic comparison. No attribution of 119 losses or general strength from these labels.',
    'new_games':0,'formalNI_Sigma_actual_go':False,'old_results_integrated':False}
save(DATA/'final-results.json', result)
bindings=read(RUN/'source-bindings.json')
checks=[]
for name,binding in bindings.items():
    p=ROOT/binding['path'];assert sha(p)==binding['original_SHA256'];checks.append({'name':name,'path':str(p.relative_to(ROOT)),'SHA256':sha(p),'unchanged':True})
for relative, expected in [('models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx','d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'),('.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm','1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'),('research-data/ai-sigma/127-tactical-oracle/labels-and-inputs.json','0c63b9eb1450d824c45786c3c73aec62f0908f87d4d14f14eacaefed7b8adc26')]:
    assert sha(ROOT/relative)==expected;checks.append({'path':relative,'SHA256':expected,'unchanged':True})
save(DATA/'input-after.json', {'necessary_inputs_only':checks})
files=sorted(p for p in OUT.rglob('*') if p.is_file() and not any(k in ['t','xdg-cache','xdg-config'] for k in p.relative_to(OUT).parts) and 'private-index' not in p.name)
members=[{'path':str(p.relative_to(OUT)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in files]
archive=DATA/'runs-all-attempts.tar.gz'
with tarfile.open(archive,'w:gz') as t:
    for p in files:t.add(p,arcname=str(p.relative_to(OUT)),recursive=False)
with tarfile.open(archive) as t:
    for member in members:assert hashlib.sha256(t.extractfile(member['path']).read()).hexdigest()==member['SHA256']
save(DATA/'archive-manifest.json', {'issue':'quoridor-4lc.129','SHA256':sha(archive),'members':members,'stream_restore_all_member_SHA':True,'source_Git':'766605299347c46869a2154afe27412162917d2f','restore_relative_to':str(OUT.relative_to(ROOT)),'models_shared_not_copied':True})
print(json.dumps({'normal_pass':8,'stress_pass':4,'stop_SHA':sha(DATA/'runtime-source-stopped-before-report.json'),'identity_union':len(identities),'resources':resources,'archive_SHA':sha(archive)}))
