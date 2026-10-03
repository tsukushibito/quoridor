"""Own CPU admission, bounded process and RSS supervision. No external signals."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

D = Path('research-data/ai-sigma/162-pv-cpu-smoke')
T = Path('tools/ai-sigma-pv-cpu-smoke')
STOP = Path('research-data/ai-sigma/159-cpu-concurrency/science-stop.json')
BOOT = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
GUARD = 896*1024**2


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2)+'\n')


def table():
    result = {}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            stat = (directory/'stat').read_text().split(') ')[1].split()
            cmd = (directory/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            result[int(directory.name)] = {'pid': int(directory.name), 'ppid': int(stat[1]), 'starttick': stat[19],
                                            'rss_bytes': int(stat[21])*os.sysconf('SC_PAGE_SIZE'), 'state': stat[0], 'cmd': cmd,
                                            'affinity': sorted(os.sched_getaffinity(int(directory.name)))}
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return result


def minimal_issue(identifier):
    p = subprocess.run(['bash', 'scripts/dev/beads.sh', 'show', identifier, '--json'], capture_output=True, text=True, timeout=10)
    if p.returncode:
        raise RuntimeError('BEADS_READ_ERROR:'+p.stderr[-200:])
    value = json.loads(p.stdout)
    value = value[0] if isinstance(value, list) else value
    return {k: value.get(k) for k in ('id', 'status', 'assignee', 'labels')}


def admit(mode):
    now = datetime.datetime.now(datetime.timezone.utc)
    assert now < datetime.datetime.fromisoformat('2026-10-03T03:55:00+00:00'), 'NEW_HEAVY_DEADLINE'
    goal, own = minimal_issue('quoridor-4lc'), minimal_issue('quoridor-4lc.162')
    assert goal['status'] == own['status'] == 'in_progress'
    assert 'paused' not in (goal['labels'] or []) and 'paused' not in (own['labels'] or []), 'PAUSED'
    assert own['assignee'] == 'codex:01a0f31c-2e4b-7170-82c5-69e1428c2418', 'OWNERSHIP'
    stop_bytes = STOP.read_bytes()
    assert hashlib.sha256(stop_bytes).hexdigest() == 'f1ed53ca0137932fca331d082b845c552671136387d954fb532c2bf0b3c4a034'
    stop = json.loads(stop_bytes)
    assert stop['scientific_jobs_finished'] and stop['scientific_source_write_stopped']
    assert stop['boot_id'] == BOOT
    current = table()
    identity_count = 0
    for job in stop['jobs']:
        assert not job['remaining'] and not job['unknown'] and not job['current_same_identity']
        path = Path('.artifacts/ai-sigma/resume-20261003/CPU-CONCURRENCY/runs')/(job['name']+'.process.json')
        b = path.read_bytes()
        assert hashlib.sha256(b).hexdigest() == job['process_sha256']
        process = json.loads(b)
        assert not process['remaining'] and not process['unknown_adopted']
        for item in process['tracked']:
            identity_count += 1
            actual = current.get(item['pid'])
            assert actual is None or actual['starttick'] != str(item['start_ticks']), '159_IDENTITY_CURRENT'
    research = [item for item in current.values() if ('/workspaces/quoridor' in item['cmd'] or '.artifacts/ai-sigma/' in item['cmd'] or 'ai-sigma-' in item['cmd']) and item['pid'] != os.getpid()]
    known_scope = ('ai-sigma-pv-cpu-smoke', 'ai-sigma-formal-clock', 'research-team', 'beads', 'git ', 'pack', 'coordinator')
    heavy = []
    for item in research:
        c = item['cmd']
        if 'ai-sigma-cpu-concurrency' in c and any(x in c for x in ('arena.cjs', 'runner.py', 'browser.cjs')):
            heavy.append(item)
        if ('chrome' in c.lower() or 'chromium' in c.lower()) and 'ai-sigma-formal-clock' not in c:
            heavy.append(item)
        if any(x in c for x in ('training.sh', 'toy.py train', 'train.py', 'selfplay', 'SIGMA-WEB-PORT')) and 'ai-sigma-pv-cpu-smoke' not in c:
            heavy.append(item)
    # Optional161 occupies its own core2/2GiB allocation. Its current RSS is measured;
    # its future guard is reserved in the sum rather than inferred from absence.
    foreign_rss = sum(item['rss_bytes'] for item in research)
    assert not heavy, 'FOREIGN_HEAVY_CURRENT'
    assert foreign_rss + 1024**3 + 2*1024**3 < 8*1024**3, 'PARENT_RAM_HEADROOM'
    available = next(int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    assert available > 1024**3, 'HOST_HEADROOM'
    current_storage = sum(p.stat().st_size for base in (D,T) for p in base.rglob('*') if p.is_file())
    forecast = current_storage + 64*1024 + 64*1024 + 160*1024
    assert forecast < 524288, 'SELF_STORAGE_FORECAST'
    assert 13974439+524288 < 14*1024**2, 'COMBINED_STORAGE'
    logs = [json.loads(p.read_text()) for p in D.glob('job-*.json')]
    elapsed = sum(x.get('elapsed_seconds', 0) for x in logs)
    assert elapsed < 120, 'CPU_TOY_CUMULATIVE'
    assert mode == 'export' or not (D/'training-attempt.json').exists(), 'TRAIN_RUN_ALREADY_ATTEMPTED'
    if mode == 'export':
        assert (D/'toy-checkpoint.pt').exists(), 'CHECKPOINT_MISSING'
    return {'UTC': now.isoformat(), 'goal': goal, 'own': own, '159_science_stop_sha256': hashlib.sha256(stop_bytes).hexdigest(),
            '159_exact_identities_currently_absent': identity_count, 'boot': BOOT,
            'current_research_processes': research, 'foreign_RSS_current_bytes': foreign_rss,
            'parent_forecast_bytes': foreign_rss+3*1024**3, '161_optional_reserved_bytes': 2*1024**3,
            'CPU': {'own_logical': [0], 'count': 1, '161_optional': [2], 'parent_limit_count': 4},
            'host_MemAvailable_bytes': available, 'self_current_bytes': current_storage,
            'self_forecast_bytes': forecast, 'combined_forecast_bytes': 14498727,
            'reservation_addition': 0, 'old_unknown_discount': 0, 'prior_toy_seconds': elapsed,
            'current_absent_not_natural_or_all_period_guarantee': True}


def main():
    mode = sys.argv[1]
    assert mode in ('train','export')
    ordinal = len(list(D.glob('job-*.json')))
    run = mode+'-'+str(ordinal)
    try:
        admission = admit(mode)
    except Exception as exc:
        dump(D/('admission-failure-'+str(time.time_ns())+'.json'), {'error_type':type(exc).__name(),'error':str(exc),'child_started':False,'epoch':time.time()})
        raise
    dump(D/('admission-'+run+'.json'), admission)
    if mode == 'train':
        dump(D/'training-attempt.json', {'run':run,'epoch':time.time(),'scientific_training_retry_forbidden':True})
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES':'', 'OMP_NUM_THREADS':'1', 'MKL_NUM_THREADS':'1', 'OPENBLAS_NUM_THREADS':'1',
           'NUMEXPR_NUM_THREADS':'1','UV_NO_SYNC':'1','UV_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1', 'TMPDIR':str(D.resolve()), 'PYTHONHASHSEED':'80311'}
    python = Path(os.environ.get('QUORIDOR_TRAINING_ENV',str(Path.home()/'.cache/inference/envs/quoridor-training')))/'bin/python'
    command = ['taskset','-c','0',str(python),str(T/'toy.py'),mode]
    start = time.time()
    deadline = min(start+90, start+120-admission['prior_toy_seconds'], datetime.datetime.fromisoformat('2026-10-03T04:00:00+00:00').timestamp())
    observed = {}; peak = 0; stop_reason = None
    log = open(D/('job-'+run+'.log'),'xb')
    child = subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    initial = table()[child.pid]
    dump(D/('started-'+run+'.json'), {'epoch':start,'deadline':deadline,'command':command,'child_identity':initial,'boot':BOOT,'source_sha256':hashlib.sha256((T/'toy.py').read_bytes()).hexdigest(),'preregister_sha256':hashlib.sha256((D/'preregister.json').read_bytes()).hexdigest()})
    while child.poll() is None:
        current = table(); own = {os.getpid(),child.pid}
        changed = True
        while changed:
            added = {pid for pid,item in current.items() if item['ppid'] in own and pid not in own}
            changed = bool(added); own |= added
        rss = sum(current[pid]['rss_bytes'] for pid in own if pid in current)
        peak = max(peak,rss)
        for pid in own:
            if pid not in current: continue
            item=current[pid]; observed[(pid,item['starttick'])]={k:item[k] for k in ('pid','ppid','starttick','rss_bytes','affinity','state')}
            try:
                for task in (Path('/proc')/str(pid)/'task').iterdir():
                    try:
                        if os.sched_getaffinity(int(task.name)) != {0}: stop_reason='OWN_TID_AFFINITY'
                    except ProcessLookupError: pass
            except FileNotFoundError: pass
        if rss>=GUARD: stop_reason='OWN_CURRENT_RSS_GUARD'
        if time.time()>=deadline: stop_reason='JOB_OR_CUMULATIVE_DEADLINE'
        if stop_reason:
            # Only the exact owned child is signalled; toy has no subprocess API.
            if child.poll() is None: child.terminate()
            break
        time.sleep(.10)
    try: child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill(); child.wait(timeout=5); stop_reason=(stop_reason or '')+' OWN_FORCED_KILL'
    log.close(); current=table()
    remaining=[v for (pid,tick),v in observed.items() if pid != os.getpid() and pid in current and current[pid]['starttick']==tick]
    result={'run':run,'start_epoch':start,'end_epoch':time.time(),'elapsed_seconds':time.time()-start,'returncode':child.returncode,
            'stop_reason':stop_reason,'peak_observed_own_plus_manager_RSS_bytes':peak,'current_owned_children_remaining':remaining,
            'outer_owned_wait_complete':child.poll() is not None,'outer_remaining_unknown':[], 'observed_identities':list(observed.values()),
            'instant_RSS_sampling_not_full_period_guarantee':True,'manager_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'toy_source_sha256':hashlib.sha256((T/'toy.py').read_bytes()).hexdigest(),'command':command,'new_teacher_game_Chrome_GPU':0}
    dump(D/('job-'+run+'.json'),result)
    assert not remaining, 'OWN_CHILDREN_REMAINING'
    print(json.dumps({k:v for k,v in result.items() if k!='observed_identities'}))
    sys.exit(child.returncode if child.returncode>=0 else 128-child.returncode)


if __name__=='__main__': main()
