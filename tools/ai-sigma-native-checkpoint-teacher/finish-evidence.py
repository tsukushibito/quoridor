"""NN0 stop/cost evidence; never starts or retries scientific work."""
import datetime, hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
A = ROOT / '.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER'
D = ROOT / 'research-data/ai-sigma/181-checkpoint-teacher'
T = pathlib.Path(__file__).resolve().parent
def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def current(pid):
    try:
        s = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return int(s[19])
    except FileNotFoundError:
        return None
attempts = []
live = []
for p in sorted((A / 'runs').glob('native181-*.process.json')):
    j = json.loads(p.read_text())
    assert not j['remaining'] and not j['unknown_adopted']
    ids = [(j['runner_pid'], j['runner_starttick'])]
    ids += [(x['pid'], x['start_ticks']) for x in j['tracked']]
    for pid, tick in ids:
        if current(pid) == tick:
            live.append({'run': j['name'], 'pid': pid, 'start_ticks': tick})
    attempts.append(dict(run=j['name'], phase=j['phase'], start=j['start'], end=j['end'],
        wall_seconds=(datetime.datetime.fromisoformat(j['end'])-datetime.datetime.fromisoformat(j['start'])).total_seconds(),
        exit=j['exit'], stop_reason=j['stop_reason'], peak_RSS=j['peak_group_plus_runner_RSS'],
        final_allocated_bytes=j['final_allocated_bytes'], remaining=j['remaining'],
        unknown=j['unknown_adopted'], command=j['cmd'], receipt=str(p.relative_to(ROOT))))
assert not live, live
summary = json.loads((D / 'dataset-summary.json').read_text())
export = json.loads((D / 'learner-export.json').read_text())
cost = dict(issue='quoridor-4lc.181', attempts=attempts,
    recorded_all_guardian_jobwall_seconds=sum(a['wall_seconds'] for a in attempts),
    heavy_budget_seconds=1800, search_hand_NN=21600+summary['NN'], hand_NN_budget=240000,
    startup_NN_separate=12, learner_ONNX_check_forward_rows_separate=10,
    conditional_K64_benchmark_games=6, conditional_benchmark_started=0,
    conditional_benchmark_reason='Prospective checkpoint adoption criterion unmet; all six NOT_STARTED',
    production_Rpolicy=summary['Rpolicy'], production_Rz=summary['Rz'], production_Rjoint=summary['Rjoint'],
    production_all_jobwall_seconds=summary['all_generation_job_wall_seconds'],
    production_export_seconds=summary['export_validate_compress_wall_seconds'],
    learner_whole_python_seconds=export['whole_python_seconds'],
    learner_whole_python_is_nested_in_guardian_jobwall=True,
    preparation_opening_generation_seconds=None, analysis_seconds=None, Git_pack_backup_seconds=None,
    other_prelaunch_management_seconds=None,
    unknown_costs_not_zero=True, API_pipe_spans_overlap_not_exclusive_CPU=True,
    all_pipeline_prep_record_learning_cost_is_distinct_from_production_rate=True)
save('cost-ledger.json', cost)
save('science-stop.json', dict(issue='quoridor-4lc.181',
    UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    last_scientific_child_end=max(a['end'] for a in attempts),
    scientific_source_writing_stopped=True, new_scientific_searches_prohibited=True,
    science_children_reaped=True, current_matching_owned_identities=live,
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(T.iterdir()) if p.is_file() and p.name not in ['save-tree.py','finish-evidence.py','pack.py','README.md']},
    selected_kernel_identity_check_not_all_host_guarantee=True,
    remaining_work='NN0 evidence pack/Git restoration/backup and handoff only'))
print(json.dumps(dict(all_jobwall=cost['recorded_all_guardian_jobwall_seconds'], hand_NN=cost['search_hand_NN'], matching_owned=live)))
