"""Finalize stopped records; no browser launch or game replay is performed."""
import collections
import datetime
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX'
DATA = ROOT / 'research-data/ai-sigma/119-diverse-prefix'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

processes = [json.loads(p.read_text()) for p in (OUT / 'runs').glob('*.process.json')]
identities = {}
for process in processes:
    assert not process['remaining'] and not process['unknown_adopted']
    assert process['exit'] == 0 and not process['stop_reason']
    identities[(process['runner_pid'], process['runner_starttick'])] = {'pid': process['runner_pid'], 'start_ticks': process['runner_starttick']}
    for identity in process['tracked']:
        identities[(identity['pid'], identity['start_ticks'])] = identity
live = []
for pid, tick in identities:
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) == tick:
            live.append({'pid': pid, 'start_ticks': tick})
    except FileNotFoundError:
        pass
assert not live

selected_roots = []
stop_per_pair = []
restored = []
for pair in range(1, 9):
    run = f'prefix119-pair{pair}-r1'
    manifest = json.loads((DATA / (run + '.manifest.json')).read_text())
    archive = DATA / (run + '.tar.gz')
    assert sha(archive) == manifest['SHA256']
    with tarfile.open(archive) as tar:
        for member in manifest['members']:
            assert hashlib.sha256(tar.extractfile(member['path']).read()).hexdigest() == member['SHA256']
        result = json.load(tar.extractfile(f'runs/{run}/browser-result.json'))
        drop = json.load(tar.extractfile(f'runs/{run}/finally-model-drop.json'))
        timers = json.load(tar.extractfile(f'runs/{run}/main-timers-stop.json'))
        controlled = json.load(tar.extractfile(f'runs/{run}/outer-controlled-stop.json'))
        assert drop['handles'] == drop['activeNN'] == 0 and len(drop['players']) == 2
        assert timers['main_timers'] == 0 and not timers['pending_messages']
        assert controlled['remaining_pids'] == 0
        groups = collections.defaultdict(list)
        for index, row in enumerate(result['rows']):
            groups[row['spec']['game_id']].append((index, row))
        for game, rows in groups.items():
            first = rows[0]
            later = next((item for item in rows[1:] if item[1].get('gate') and not item[1]['gate']['missing_public_cp']), None)
            for label, item in [('first', first), ('first_eligible_later', later)]:
                selected_roots.append({'run': run, 'game': game, 'selection': label, 'row_index': item[0] if item else None, 'engine': item[1]['spec']['engine'] if item else None, 'P2': item[1]['gate']['P2canonical'] if item else None, 'fixed_NN_reference': False})
        stop_per_pair.append({'run': run, 'models_zero': True, 'main_timer_message_zero': True, 'inner_controlled_remaining': 0, 'outer_wait_record': run + '.process.json'})
    restored.append({'archive': archive.name, 'SHA256': manifest['SHA256'], 'all_member_hashes_restored': True})
save(DATA / 'selected-root-indices.json', {'rule': 'preregister first root and first eligible later root of each game; indices only, not new NN samples', 'selected': selected_roots, 'all_saved_root_self_gate_denominator': 764, 'new_prefix_fixed_reference_roots': 0, 'startup_fixed_gold_roots': 48})

result = json.loads((DATA / 'final-results.json').read_text())
seconds = lambda p: (datetime.datetime.fromisoformat(p['end']) - datetime.datetime.fromisoformat(p['start'])).total_seconds()
resources = {'RSS_peak': max(p['peak_group_plus_runner_RSS'] for p in processes), 'storage_peak': max(p['peak_allocated_bytes'] for p in processes), 'heavy_seconds': sum(seconds(p) for p in processes if p['phase'] != 'protocol'), 'pure_seconds': sum(seconds(p) for p in processes if p['phase'] == 'protocol'), 'current_RSS_not_ru_maxrss': True, 'instantaneous_peak_background_CPU_final_exited_child_CPU_and_short_metadata_commands_unobserved': True, 'observed_affinity_violations': sum(len(p['affinity_violations']) for p in processes)}
result['resources'] = resources
result['candidate_color_WDL'] = {str(color): dict(collections.Counter(g['candidate_result'] for g in result['games'] if g['candidate_color'] == color)) for color in [1, 2]}
save(DATA / 'final-results.json', result)
source = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'tools/ai-sigma-diverse-prefix').glob('*') if p.is_file()}
stop = {'issue': 'quoridor-4lc.119', 'UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'source_runtime_stopped': True, 'process_runs': len(processes), 'recorded_identities': len(identities), 'recorded_identity_list': list(identities.values()), 'current_same_identity': live, 'remaining_unknown_per_run': 0, 'pair_cleanup': stop_per_pair, 'source_after': source, 'resources': resources, 'measurement_versions': ['8124d876ed69128f16485f8d6b7216171e792789', '532c87349fa0baf233fa905f5f3d8c88a5560a9f'], 'post_measurement_admission_fix': 'proc executable readlink and live-empty-command rejection tested NN0; actual eight browser runs used argv[0] identification, not retrospective proof of final guard', 'current_absence_not_natural_or_all_period_proof': True, 'final_metadata_commands_not_managed_runtime_identity_union': True}
save(OUT / 'runtime-source-stopped-before-report.json', stop)
save(DATA / 'runtime-source-stopped-before-report.json', stop)

files = sorted(p for p in OUT.rglob('*') if p.is_file() and not any(part in ['t', 'xdg-cache', 'xdg-config'] for part in p.relative_to(OUT).parts) and 'private-index' not in p.name)
archive = DATA / 'setup-generation-stop.tar.gz'
members = [{'path': str(p.relative_to(OUT)), 'SHA256': sha(p), 'bytes': p.stat().st_size} for p in files]
with tarfile.open(archive, 'w:gz') as tar:
    for p in files:
        tar.add(p, arcname=str(p.relative_to(OUT)), recursive=False)
with tarfile.open(archive) as tar:
    for member in members:
        assert hashlib.sha256(tar.extractfile(member['path']).read()).hexdigest() == member['SHA256']
save(DATA / 'setup-generation-stop.manifest.json', {'SHA256': sha(archive), 'members': members, 'stream_restored': True})
save(DATA / 'archive-restoration.json', {'pair_archives': restored, 'setup_archive_SHA256': sha(archive), 'all_stream_member_hashes_match': True})
print(json.dumps({'stop_SHA256': sha(DATA / 'runtime-source-stopped-before-report.json'), 'process_runs': len(processes), 'identities': len(identities), 'current_live': live, 'selected_roots': len(selected_roots), 'resources': resources}))
