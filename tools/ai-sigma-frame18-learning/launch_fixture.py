"""Own only one bounded NN0 fixture family; reject physical computation overlap."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import resource
import subprocess
import sys
import time

R = Path(__file__).resolve().parents[2]
T = R / 'tools/ai-sigma-frame18-learning'
D = R / 'research-data/ai-sigma/frame18-learning-connection-view/adapter-preparation'
ACTOR = 'codex:01a0f31c-2e4b-7170-82c5-69e1428c2418'
GUARD = 448 * 1024 ** 2


def utc():
    return datetime.datetime.now(datetime.timezone.utc)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def table():
    rows = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            s = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            args = (p / 'cmdline').read_bytes().decode().split('\0')
            script = next((a for a in args[1:5] if a.endswith(('.py', '.cjs', '.js', '.sh'))
                           and ' ' not in a and '\n' not in a and Path(a).is_file()), '')
            rows[int(p.name)] = {'pid': int(p.name), 'ppid': int(s[1]), 'pgrp': int(s[2]),
                                 'tick': s[19], 'state': s[0], 'RSS': int(s[21]) * os.sysconf('SC_PAGE_SIZE'),
                                 'script': script, 'argv': ' '.join(args)[:400],
                                 'affinity': sorted(os.sched_getaffinity(int(p.name)))}
        except (OSError, ValueError, UnicodeError):
            pass
    return rows


def family(rows, pid):
    ids = {pid}
    while True:
        more = ids | {p for p, r in rows.items() if r['ppid'] in ids}
        if more == ids:
            return [r for p, r in rows.items() if p in ids]
        ids = more


def admit():
    controls = []
    env = dict(os.environ, BEADS_ACTOR=ACTOR)
    for issue in ('quoridor-4lc', 'quoridor-4lc.227'):
        q = json.loads(subprocess.check_output(['bash', 'scripts/dev/beads.sh', 'show', issue, '--json'],
                                             cwd=R, env=env, timeout=10))[0]
        assert q['status'] == 'in_progress' and 'paused-by-user' not in q.get('labels', [])
        if issue.endswith('.227'):
            assert q['assignee'] == ACTOR
        controls.append({k: q.get(k) for k in ('id', 'status', 'assignee', 'labels')})
    loadedpath = R / '.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame18/running-loaded.json'
    loaded = json.loads(loadedpath.read_text())
    sch = json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
    assert sch['phase'] == 'running' and not sch.get('recovery_required')
    assert loaded['start_fixed'] == '2026-10-04T10:33:18Z' and loaded['end'] == '2026-10-04T14:33:18Z'
    assert loaded['max_turn_seconds'] is None
    assert hashlib.sha256((R / 'docs/design/ai-sigma-continuation-20261001.md').read_bytes()).hexdigest() == loaded['parent_sha']
    assert sch['config_sha256'] == hashlib.sha256(Path(sch['config_path']).read_bytes()).hexdigest()
    assert sch['contract_sha256'] == hashlib.sha256(Path(sch['binding']['contract_file']).read_bytes()).hexdigest()
    rows = table()
    for name in ('scheduler', 'monitor'):
        ident = loaded[name].get('process', loaded[name])
        assert ident['pid'] in rows and rows[ident['pid']]['tick'] == str(ident['start_ticks'])
    mon = Path(loaded['run']) / 'monitor-observation.json'
    assert time.time() - mon.stat().st_mtime < 120, 'CURRENT_MONITOR_STALE'
    foreign, services = [], []
    for pid, r in rows.items():
        if pid == os.getpid() or r['state'] == 'Z':
            continue
        script = r['script']
        research = ('tools/ai-sigma-' in script or 'tools/nnue-training/' in script or
                    'research-data/ai-sigma/' in script or 'faithful-native' in r['argv'])
        if research and not script.endswith(('/save.py', '/save_git.py', '/pack.py')):
            foreign.append(r)
        elif research or 'tools/research-team/' in script or 'SIGMA-RESUME-OPERATIONS-92/' in script:
            services.append(r)
    assert not foreign, 'CURRENT_FOREIGN_COMPUTE: ' + repr(foreign)
    # An owned LLM turn by itself is not a gate; actual CPU0 guard is foreign above.
    quiet = sch.get('next_at', 0) - time.time()
    assert quiet >= 35, 'NEXT_NATURAL_CPU0_WINDOW_SHORT'
    rss = sum(r['RSS'] for r in services)
    assert rss + 512 * 1024 ** 2 < 8 * 1024 ** 3
    forecast = json.loads((D / 'storage-forecast.json').read_text())
    assert forecast['forecast_B'] < 2 * 1024 ** 2 < 3 * 1024 ** 2 and forecast['additional_reservation_B'] == 0
    sources = json.loads((D / 'source-freeze.json').read_text())
    for path, sha in sources['files'].items():
        assert hashlib.sha256((R / path).read_bytes()).hexdigest() == sha, 'SOURCE_CHANGED: ' + path
    return {'UTC': utc().isoformat(), 'controls': controls, 'foreign': foreign,
            'services': services, 'scheduler_owned': sch.get('owned'), 'quiet_seconds': quiet,
            'runtime_SHA': hashlib.sha256(loadedpath.read_bytes()).hexdigest(),
            'runtime_current_identities': {k: rows[loaded[k].get('process', loaded[k])['pid']] for k in ('scheduler', 'monitor')},
            'parent_RSS_forecast_B': rss + 512 * 1024 ** 2, 'storage': forecast}


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--id', required=True)
    args = parser.parse_args()
    assert '/' not in args.id and args.id not in ('.', '..')
    latest = datetime.datetime.fromisoformat('2026-10-04T11:35:18+00:00')
    assert utc() < latest and utc() + datetime.timedelta(seconds=35) < datetime.datetime.fromisoformat('2026-10-04T11:38:18+00:00')
    job = D / 'jobs' / args.id
    job.mkdir(parents=True, exist_ok=False)
    try:
        admission = admit()
    except Exception as exc:
        write(job / 'not-started.json', {'UTC': utc().isoformat(), 'status': 'NOT_STARTED_ADMISSION',
                                        'error': str(exc), 'NN': 0, 'fixture_child': 0})
        raise
    write(job / 'admission.json', admission)
    os.sched_setaffinity(0, {0})
    command = [sys.executable, '-B', str(T / 'fixture.py'), '--out', str(job / 'synthetic')]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
    start = time.monotonic();peak = 0;identities = {};reason = 'completed'
    with (job / 'stdout.txt').open('wb') as stdout, (job / 'stderr.txt').open('wb') as stderr:
        child = subprocess.Popen(command, cwd=R, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        actual_identity = table().get(child.pid)
        if actual_identity:
            identities[(actual_identity['pid'], actual_identity['tick'])] = actual_identity
        write(job / 'actual-start.json', {'UTC': utc().isoformat(), 'command': command, 'CPU': [0], 'threads': 1,
                                         'identity': actual_identity, 'NN': 0})
        while child.poll() is None:
            rows = table();members = family(rows, child.pid)
            for r in members:
                identities[(r['pid'], r['tick'])] = r
            rss = sum(r['RSS'] for r in members) + rows[os.getpid()]['RSS'];peak = max(peak, rss)
            if rss >= GUARD or time.monotonic() - start >= 5:
                reason = 'RAM_GUARD' if rss >= GUARD else 'HARD_TIMEOUT'
                os.killpg(child.pid, signal.SIGTERM)
                try: child.wait(timeout=1)
                except subprocess.TimeoutExpired: os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(.01)
        code = child.wait()
    rows = table();remaining = [rows[p] for p, tick in identities if p in rows and rows[p]['tick'] == tick]
    assert child.pid not in rows, 'waited child PID unexpectedly still exists'
    if remaining:
        os.killpg(child.pid, signal.SIGKILL);child.wait();reason = 'CHILD_REMAINS'
    assert not remaining, 'owned fixture descendants remain'
    receipt = {'UTC': utc().isoformat(), 'exit': code, 'reason': reason, 'wall_seconds': time.monotonic() - start,
               'family_peak_RSS_B': peak, 'guard_B': GUARD, 'CPU': [0], 'threads': 1,
               'child_past_peak_RSS_B': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024,
               'owned_identities': list(identities.values()), 'child_wait': True, 'current_exact': remaining,
               'NN': 0, 'model_imports': 0, 'train': 0, 'real_labels': 0}
    write(job / 'process.json', receipt);print(json.dumps(receipt))
    if code:
        raise SystemExit(code)


if __name__ == '__main__':
    main()
