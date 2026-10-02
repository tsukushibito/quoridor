"""Preserve all stopped count attempts and finite A/B/C evidence, no new NN."""
import collections
import datetime
import hashlib
import json
import math
import statistics
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/COMPLETED-FPU'
DATA=ROOT/'research-data/ai-sigma/123-completed-fpu'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def distribution(values):
    values=list(values)
    return {'n':len(values),'min':min(values) if values else None,'median':statistics.median(values) if values else None,'max':max(values) if values else None}

attempts=[];comparisons=[];model_costs=[];cleanup=[]
for run in ['fpu123-count-r2','fpu123-count-r3']:
    directory=OUT/'runs'/run
    raw=json.loads((directory/'browser-result.json').read_text())
    comparisons.extend(raw['comparisons'])
    for row in raw['count_results']:
        row['run']=run;attempts.append(row)
    costs=json.loads((directory/'model-load.json').read_text())
    model_costs.append({'run':run,'initialization':costs,'startup':json.loads((directory/'startup.json').read_text()),'end_clocks':json.loads((directory/'clock-end.json').read_text())})
    drop=json.loads((directory/'finally-model-drop.json').read_text())
    timer=json.loads((directory/'main-timers-stop.json').read_text())
    monitor=json.loads((directory/'pause-monitor-stop.json').read_text())
    controlled=json.loads((directory/'outer-controlled-stop.json').read_text())
    assert drop['handles']==drop['activeNN']==0 and len(drop['players'])==2
    assert timer['main_timers']==0 and not timer['pending_messages']
    assert monitor['all_owned_read_callbacks_waited'] and not monitor['pending_children'] and not monitor['active_monitor_timer']
    assert controlled['remaining_pids']==0 and controlled['waited'] and controlled['zombie_identities_absent']
    cleanup.append({'run':run,'Models2_zero':True,'main_timer_message_zero':True,'monitor_callbacks_waited':True,'inner_forced':controlled['forced'],'innercontrolled_remaining':0,'outer_owned_wait':run+'.process.json'})
successful=[row for row in attempts if not row.get('primary') and not row.get('main_gate_error')]
failed=[row for row in attempts if row not in successful]
assert len(successful)==15 and len(failed)==1
assert failed[0]['NN_calls']==0 and failed[0]['completed_backups']==0 and failed[0]['root_node'] is None and failed[0]['cp'] is None
assert len({(row['fixture_id'],row['condition']) for row in successful})==15
assert all(row['completed_backups']==row['observed_root_N']==32 and row['edge_sum']==31 for row in successful)
fpu_checks=[]
for row in successful:
    assert row['zero']=={'handles':0,'activeNN':0,'active':False,'mode':'original'}
    if row['condition']=='A':
        assert row['root_node'] is None and row['candidate_parentQ_missing']
        continue
    root=row['root_node'];assert root['truevisitCount']==32 and root['parentQ']==root['valueSum']/32
    assert math.isfinite(root['valueSum']) and abs(root['parentQ'])<=1
    assert len(row['root_FPU_selections'])==31
    for event in row['root_FPU_selections']:
        assert event['parentQ']==event['valueSum']/event['truevisitCount']
        assert event['original_unvisitedQ']==event['parentQ']-.2*math.sqrt(event['visitedChildBasePriorSum'])
        assert event['used_unvisitedQ']==(0 if row['condition']=='C' else event['original_unvisitedQ'])
    fpu_checks.append({'fixture':row['fixture_id'],'condition':row['condition'],'true_root_node_observed':True,'selection_events':31,'mode_correct':True,'trueparentQ_not_edge_average':True})

processes=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*.process.json')]
identities={}
for process in processes:
    assert process['exit']==0 and not process['stop_reason'] and not process['remaining'] and not process['unknown_adopted']
    for identity in process['tracked']+[{'pid':process['runner_pid'],'start_ticks':process['runner_starttick']}]:identities[identity['pid'],identity['start_ticks']]=identity
# The first runner failed before child creation. Keep its exact launcher identity separately.
first=json.loads((OUT/'runs/fpu123-count-r1.monitor.jsonl').read_text().splitlines()[0])['launcher']
identities[first['pid'],first['start_ticks']]=first
live=[]
for pid,tick in identities:
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        if int(fields[19])==tick:live.append({'pid':pid,'start_ticks':tick})
    except FileNotFoundError:pass
assert not live
seconds=lambda p:(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds()
resources={'managed_heavy_seconds':sum(seconds(p) for p in processes if p['phase']!='protocol'),'managed_static_seconds':sum(seconds(p) for p in processes if p['phase']=='protocol'),'RSS_peak':max(p['peak_group_plus_runner_RSS'] for p in processes),'storage_peak':max(p['peak_allocated_bytes'] for p in processes),'observed_affinity_violations':sum(len(p['affinity_violations']) for p in processes),'first_prelaunch_failure_not_in_managed_wall':True,'currentRSS_not_ru_maxrss':True,'instantaneous_peak_background_CPU_and_short_metadata_unobserved':True}
stop={'issue':'quoridor-4lc.123','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_runtime_stopped':True,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'managed_runs':len(processes),'prelaunch_failures':1,'recorded_identity_union':len(identities),'identities':list(identities.values()),'current_same_identity':live,'remaining_unknown':0,'cleanup':cleanup,'resources':resources,'source_after':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'tools/ai-sigma-completed-fpu').iterdir() if p.is_file()},'current_absence_not_natural_or_all_period_proof':True}
save(OUT/'runtime-source-stopped-before-report.json',stop);save(DATA/'runtime-source-stopped-before-report.json',stop)

metrics=[]
for row in successful:
    metrics.append({'run':row['run'],'fixture':row['fixture_id'],'condition':row['condition'],'action':row['cp']['action'],'completed_backup':row['completed_backups'],'rootN':row['observed_root_N'],'edge_sum':row['edge_sum'],'NN_calls':row['NN_calls'],'terminal_noNN':row['terminal_noNN_backups'],'entropy':row['entropy'],'depth':row.get('depth'),'caps':row.get('caps'),'root_parentQ':row['root_node']['parentQ'] if row['root_node'] else None,'wrapper_ms':row['wrapper_end_ms']-row['wrapper_start_ms'],'input_create_to_first_infer_ms':row['spans'][0]['wrapper_start_ms']-row['wrapper_start_ms'],'first_infer_wrapper_ms':row['spans'][0]['wrapper_end_ms']-row['spans'][0]['wrapper_start_ms'],'first_API_await_ms':row['spans'][0]['API_end_ms']-row['spans'][0]['API_start_ms'],'first_CP_ms':row['first_CP_ms']-row['wrapper_start_ms'],'all_API_await_sum_ms':sum(x['API_end_ms']-x['API_start_ms'] for x in row['spans']),'all_infer_wrapper_sum_ms':sum(x['wrapper_end_ms']-x['wrapper_start_ms'] for x in row['spans']),'cleanup_included_in_wrapper':True,'isolated_search_cleanup_span_missing':True})
result={'issue':'quoridor-4lc.123','planned_conditions':15,'actual_tree_searches':15,'completed_K32':15,'completed_backup':sum(row['completed_backups'] for row in successful),'search_transport_attempts':16,'presearch_schema_failures':1,'failed_searches_after_tree_or_NN_start':0,'admission_launch0_failures':1,'unexecuted_conditions':0,'search_NN':sum(row['NN_calls'] for row in attempts),'startup_NN':12,'terminal_noNN_backup':sum(row['terminal_noNN_backups'] for row in successful),'fixed_golden_search_root_gates':9,'prefix_self_search_root_gates':6,'all_same_input_root_NN_exact':all(x['root_inputs_AB']['NN_exact'] and x['root_inputs_BC']['NN_exact'] for x in comparisons),'FPU_trueNode_checks':fpu_checks,'comparisons':comparisons,'metrics':metrics,'FPU_changed_distribution_inputs':sum(x['TV_BC']>0 for x in comparisons),'FPU_changed_Action_inputs':sum(x['actions']['B']!=x['actions']['C'] for x in comparisons),'C_moves_closer_to_A':sum(x['TV_AC']<x['TV_AB']-1e-12 for x in comparisons),'C_moves_farther_from_A':sum(x['TV_AC']>x['TV_AB']+1e-12 for x in comparisons),'equal_distance':sum(abs(x['TV_AC']-x['TV_AB'])<=1e-12 for x in comparisons),'reference_depth_missing_original6_rows':6,'candidate_true_parentQ_missing':True,'sameK_not_sameNN_CPU_wall':True,'APIawait_not_kernel_CPU':True,'explicit_warm_searches':0,'startup_model_initialization_separate':True,'models_costs':model_costs,'resources':resources,'formal_fairness_NI_Sigma_actual_go':False,'old_results_integrated':False,'new_games':0,'conclusion':'Finite unvisited-Q sensitivity, heterogeneous direction. No proof of 119 loss cause or improvement. Keep policy; next proposal isolates true-parent candidate FPU on prefix1 and jump before another WDL run; do not infer parentQ from rootNN or edge means.'}
save(DATA/'final-results.json',result)

files=sorted(p for p in OUT.rglob('*') if p.is_file() and not any(k in ['t','xdg-cache','xdg-config'] for k in p.relative_to(OUT).parts) and 'private-index' not in p.name)
members=[{'path':str(p.relative_to(OUT)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in files]
archive=DATA/'runs-all-attempts.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for p in files:tar.add(p,arcname=str(p.relative_to(OUT)),recursive=False)
with tarfile.open(archive) as tar:
    for member in members:assert hashlib.sha256(tar.extractfile(member['path']).read()).hexdigest()==member['SHA256']
save(DATA/'archive-manifest.json',{'issue':'quoridor-4lc.123','SHA256':sha(archive),'members':members,'stream_restore_all_member_SHA':True,'source_versions':['1ca0322','33d2c13'],'restore_relative_to':'.artifacts/ai-sigma/resume-20261002/COMPLETED-FPU','model_shared_no_copy':True})
print(json.dumps({'completed_K32':15,'backup':result['completed_backup'],'search_NN':result['search_NN'],'startup_NN':12,'TV_changed_inputs':result['FPU_changed_distribution_inputs'],'Action_changed_inputs':result['FPU_changed_Action_inputs'],'identities':len(identities),'stop_SHA':sha(DATA/'runtime-source-stopped-before-report.json'),'resources':resources}))
