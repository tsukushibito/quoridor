"""Finite metadata path bound to an existing scheduler-owned supervisor turn."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path('/workspaces/quoridor/.worktree/ai-sigma')
MAIN = Path('/workspaces/quoridor')
RUNTIME = MAIN / '.artifacts/research-team/scheduler-sigma-continuation-20261001'
BASE = ROOT / '.artifacts/ai-sigma/continuation-20261001/supervisor'
THREAD = '01a0f6b5-b1bd-7752-b0bb-74a336e459a4'
UTC = dt.timezone.utc
ENV = {'UV_NO_SYNC': '1', 'UV_OFFLINE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}

class Rejected(ValueError):
    pass

def utc_now():
    return dt.datetime.now(UTC)

def parse_utc(value):
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise Rejected('Missing/invalid owned start')
    if result.tzinfo is None:
        raise Rejected('Owned start needs timezone')
    return result.astimezone(UTC)

def uuid_text(value):
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError()
    except (ValueError, AttributeError, TypeError):
        raise Rejected('Invalid run/turn UUID')
    return value

def write(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)

def proc(pid):
    try:
        f = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'start_ticks': f[19], 'state': f[0],
                'rss_bytes': int(f[21]) * os.sysconf('SC_PAGE_SIZE'),
                'affinity': list(os.sched_getaffinity(pid))}
    except (OSError, ValueError, IndexError):
        return None

def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

def binding(owned, run, turn, prior=None, wall=None, mono=None, boot=None):
    wall = wall or utc_now()
    mono = time.monotonic() if mono is None else mono
    boot = boot or boot_id()
    if not owned or owned.get('run_id') != uuid_text(run):
        raise Rejected('Run not currently owned')
    actual_turn = uuid_text(owned.get('turn_id'))
    if turn is not None and uuid_text(turn) != actual_turn:
        raise Rejected('Turn mismatch')
    if owned.get('thread_id') != THREAD or owned.get('max_turn_seconds') != 180:
        raise Rejected('Wrong target/turn contract')
    start = parse_utc(owned.get('started_at'))
    age = (wall - start).total_seconds()
    if age < 0 or not math.isfinite(mono):
        raise Rejected('Future start/invalid monotonic clock')
    core = {'run_id': run, 'turn_id': actual_turn, 'thread_id': THREAD,
            'started_at': start.isoformat(), 'boot_id': boot}
    if prior:
        if any(prior.get(k) != v for k, v in core.items()):
            raise Rejected('Binding/start/boot changed; never reset deadline')
        if mono < prior['mapped_start_monotonic']:
            raise Rejected('Monotonic clock went backwards')
        return prior
    return {**core, 'mapped_start_monotonic': mono-age, 'calibrated_at_utc': wall.isoformat(),
            'calibrated_at_monotonic': mono,
            'read_start_deadline_utc': (start+dt.timedelta(seconds=90)).isoformat(),
            'read_finish_deadline_utc': (start+dt.timedelta(seconds=120)).isoformat(),
            'turn_deadline_utc': (start+dt.timedelta(seconds=180)).isoformat(),
            'initial_mapping_limit': 'Initial UTC-to-monotonic mapping assumes no prior wall-clock jump; future/backwards boot/start is rejected.'}

def age_now(bound, wall=None, mono=None):
    wall = wall or utc_now()
    mono = time.monotonic() if mono is None else mono
    if mono < bound['mapped_start_monotonic']:
        raise Rejected('Monotonic clock went backwards')
    return max((wall-parse_utc(bound['started_at'])).total_seconds(),
               mono-bound['mapped_start_monotonic'])

def admit(bound, phase, wall=None, mono=None):
    age = age_now(bound, wall, mono)
    limit = {'read_start': 90, 'read_finish': 120, 'finish': 180}[phase]
    if age >= limit:
        raise Rejected(f'{phase} cutoff reached ({age:.6f}s >= {limit}s)')
    return age

def stamp():
    return {'utc': utc_now().isoformat(), 'monotonic': time.monotonic(), 'process': proc(os.getpid()),
            'boot_id': boot_id(), 'environment': {k: os.environ.get(k) for k in ENV},
            'rlimit_as': resource.getrlimit(resource.RLIMIT_AS), 'ram_budget_is_RSS_not_AS': True}

def cleanup_group(child):
    # New process group is exclusively this invocation's command and descendants.
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=0.4)
    except subprocess.TimeoutExpired:
        pass
    # Collect lingering descendants even if their shell parent already exited.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=1)

def sampled_rss(child_pid, background):
    items = []; seen = set(); stack = [os.getpid(), child_pid]
    # No recursive walk of scheduler/watch children: only their recorded roots.
    for expected in background:
        p = proc(expected['pid'])
        if p and p['start_ticks'] == str(expected['start_ticks']):
            items.append(p); seen.add(p['pid'])
    while stack and len(seen) < 48:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid); p = proc(pid)
        if p:
            items.append(p)
        try:
            stack.extend(int(x) for x in Path(f'/proc/{pid}/task/{pid}/children').read_text().split())
        except OSError:
            pass
    return sum(v['rss_bytes'] for v in items)

def owned_storage_bytes():
    # Bounded owner namespaces only; no shared cache/DB traversal.
    roots = [ROOT/'tools/ai-sigma-supervisor-read-guard', RUNTIME,
             ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler',
             ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE',
             ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-READ-GUARD',
             ROOT/'docs/reports/ai-sigma-steward-scheduler-live.md',
             ROOT/'docs/reports/ai-sigma-steward-supervisor-read-guard.md']
    seen = set(); total = 0
    for root in roots:
        stack = [root]
        while stack:
            p = stack.pop()
            try:
                s = p.lstat(); key = (s.st_dev, s.st_ino)
                if key not in seen:
                    total += s.st_blocks*512; seen.add(key)
                if p.is_dir() and not p.is_symlink():
                    stack.extend(p.iterdir())
            except FileNotFoundError:
                pass
    return total

def run_child(args, path, bound, phase='read', background=(), timeout=12):
    admit(bound, 'read_start' if phase == 'read' else 'finish')
    if owned_storage_bytes() >= 112*1024**2:
        raise Rejected('Combined steward allocated guard; no command launched')
    limit = 120 if phase == 'read' else 180
    started = stamp(); peak = 0; cause = None
    # AS is intentionally inherited without imposing 1GiB; Go/cgo needs virtual reserve.
    with path.with_suffix('.stdout').open('wb') as stdout, path.with_suffix('.stderr').open('wb') as stderr:
        child = subprocess.Popen(args, cwd=ROOT, stdout=stdout, stderr=stderr,
                                 env={**os.environ, **ENV}, start_new_session=True)
        ident = proc(child.pid)
        command_deadline = time.monotonic() + min(timeout, max(0, limit-age_now(bound)-2))
        try:
            while child.poll() is None:
                peak = max(peak, sampled_rss(child.pid, background))
                if peak >= 1024**3:
                    cause = 'sampled_combined_RSS_guard'; break
                if path.with_suffix('.stdout').stat().st_size + path.with_suffix('.stderr').stat().st_size > 2*1024**2:
                    cause = 'bounded_output_guard'; break
                if time.monotonic() >= command_deadline or age_now(bound) >= limit-2:
                    cause = 'timeout/deadline'; break
                time.sleep(0.02)
            if cause:
                cleanup_group(child)
            else:
                child.wait()
        except BaseException as error:
            cause = 'operator/interruption: '+type(error).__name__
            cleanup_group(child)
        finally:
            if child.poll() is None:
                cleanup_group(child)
    finished = stamp()
    row = {'command': args, 'started': started, 'finished': finished, 'child': ident,
           'exit_code': child.returncode, 'cause': cause, 'reaped': True,
           'sampled_combined_RSS_peak_bytes': peak, 'sample_interval_seconds': 0.02,
           'instant_RSS_peak_not_guaranteed': True, 'phase': phase,
           'age_started_seconds': age_now(bound, parse_utc(started['utc']), started['monotonic']),
           'age_finished_seconds': age_now(bound, parse_utc(finished['utc']), finished['monotonic'])}
    write(path, row)
    if cause or child.returncode:
        raise Rejected('Owned command failed/expired; evidence retained and child reaped')
    admit(bound, 'read_finish' if phase == 'read' else 'finish')
    return json.loads(path.with_suffix('.stdout').read_text()) if phase == 'read' else row

def live_owned(run, turn, prior):
    if prior:
        admit(prior, 'read_start')
    state = json.loads((RUNTIME/'state.json').read_text())
    b = state.get('binding') or {}
    if state.get('phase') != 'running' or state.get('recovery_required') or b.get('thread_id') != THREAD or b.get('dispatch_issue') != 'quoridor-4lc.40':
        raise Rejected('Runtime binding unavailable/unresolved')
    expected = state.get('process'); observed = proc(expected['pid']) if expected else None
    if not observed or observed['state'] == 'Z' or observed['start_ticks'] != str(expected['start_ticks']) or expected.get('boot_id') != boot_id():
        raise Rejected('Scheduler identity absent/changed')
    bound = binding(state.get('owned'), run, turn, prior)
    admit(bound, 'read_start')
    return bound, state

def observe(directory, run, turn):
    prior_path = directory/'binding.json'
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else None
    bound, state = live_owned(run, turn, prior)
    write(prior_path, bound)
    if (directory/'observation.json').exists():
        # Cached result only. No late new reads and no new deadline calibration.
        return {'cached': True, 'observation': str(directory/'observation.json'), 'binding': bound}
    background = [state['process']]
    monitor = ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE/monitor-process.json'
    if monitor.exists():
        background.append(json.loads(monitor.read_text())['process'])
    commands = [('ready', ['bash', str(MAIN/'scripts/dev/beads.sh'), 'ready', '--json']),
                ('issues', ['bash', str(MAIN/'scripts/dev/beads.sh'), 'show', 'quoridor-4lc.40',
                            'quoridor-4lc', 'quoridor-4lc.38', 'quoridor-4lc.39', 'quoridor-4lc.41', 'quoridor-4lc.42', '--json']),
                ('sessions', ['bash', str(MAIN/'scripts/dev/research-team.sh'), 'status'])]
    values = {}
    begin = stamp()
    for name, args in commands:
        # Rebind exact current owner before every new metadata command.
        current, _ = live_owned(run, bound['turn_id'], bound)
        assert current == bound
        values[name] = run_child(args, directory/(name+'.json'), bound, background=background)
    admit(bound, 'read_finish')
    issues = values['issues']
    if not isinstance(issues, list):
        raise Rejected('Unexpected issues shape; retain command raw')
    summary = [{'id': x.get('id'), 'status': x.get('status'), 'assignee': x.get('assignee'),
                'labels': x.get('labels') or [], 'notes_tail': str(x.get('notes') or '')[-1200:]} for x in issues]
    paused = any('paused-by-user' in x['labels'] for x in summary if x['id'] in ('quoridor-4lc', 'quoridor-4lc.40'))
    result = {'run_id': run, 'turn_id': bound['turn_id'], 'binding': bound, 'started': begin,
              'finished': stamp(), 'ready_ids': [x.get('id') for x in values['ready']], 'issues': summary,
              'sessions': values['sessions'], 'scheduler_snapshot': state,
              'background_identities_for_RSS': background,
              'pause_observed': paused, 'read_command_count': len(commands),
              'scripted_path_only': True, 'whole_turn_compliance_verified': False,
              'side_DB_cache_writes_not_quantified': True,
              'old_deviations_32games_goal_not_attained_preserved': True}
    write(directory/'observation.json', result)
    return result

def finish(directory, run, turn, note):
    # Only already-saved own observation/binding; no fresh issue/session/runtime reads.
    bound = json.loads((directory/'binding.json').read_text())
    uuid_text(run)
    if run != bound['run_id'] or (turn and uuid_text(turn) != bound['turn_id']) or boot_id() != bound['boot_id']:
        raise Rejected('Finish binding mismatch')
    admit(bound, 'finish')
    observation = json.loads((directory/'observation.json').read_text())
    if observation['pause_observed']:
        raise Rejected('Cached pause; no further operations')
    own = next(x for x in observation['issues'] if x['id'] == 'quoridor-4lc.40')
    if own['status'] != 'in_progress' or own['assignee'] != 'codex:'+THREAD:
        raise Rejected('Own monitor issue not claimed; do not claim/restart from stale data')
    if len(note)>4096:
        raise Rejected('Note too long')
    row = run_child(['bash', str(MAIN/'scripts/dev/beads.sh'), 'update', 'quoridor-4lc.40',
                     '--if-assignee', 'codex:'+THREAD, '--if-status', 'in_progress',
                     '--append-notes', note+' / guarded observation '+str(directory/'observation.json')],
                    directory/'notes.json', bound, phase='finish', timeout=10,
                    background=observation['background_identities_for_RSS'])
    backup = run_child(['bash', str(MAIN/'scripts/dev/beads.sh'), 'backup', 'sync'],
                       directory/'backup.json', bound, phase='finish', timeout=10,
                       background=observation['background_identities_for_RSS'])
    result = {'run_id': run, 'turn_id': bound['turn_id'], 'at': stamp(), 'operations': [row, backup],
              'owned_command_children_reaped': True, 'persistent_self_jobs_started': 0,
              'scheduler_watch_not_stopped': True, 'recorder_exits_after_record': True,
              'whole_turn_completion_pending_external_AppServer_evidence': True}
    write(directory/'self-stop.json', result)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('observe', 'finish'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--turn-id')
    parser.add_argument('--note', default='監督の保存済みバッチ観測。旧逸脱/欠測/目標未達を保持、正常なら通知0。')
    args = parser.parse_args()
    def interrupted(*_):
        raise Rejected('Owned guard interrupted; collect own command group')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    os.sched_setaffinity(0, {0}); os.environ.update(ENV)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    run = uuid_text(args.run_id)
    if os.environ.get('CODEX_THREAD_ID') != THREAD:
        raise Rejected('Caller is not the saved supervisor session')
    directory = BASE/run/'read-guard'
    # Check live binding before first filesystem creation; expired/mismatched runs fail closed.
    if args.operation == 'observe':
        prior = json.loads((directory/'binding.json').read_text()) if (directory/'binding.json').exists() else None
        live_owned(run, args.turn_id, prior)
    elif not (directory/'binding.json').exists():
        raise Rejected('No observed binding; finish cannot initialize/reset')
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/'guard.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = observe(directory, run, args.turn_id) if args.operation == 'observe' else finish(directory, run, args.turn_id, args.note)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as error:
            write(directory/('failure-'+str(time.monotonic_ns())+'.json'), {'at': stamp(), 'operation': args.operation,
                  'error': str(error), 'no_foreign_process_or_turn_stopped': True})
            raise

if __name__ == '__main__':
    try:
        main()
    except (Rejected, OSError, ValueError, subprocess.SubprocessError) as error:
        print('READ_GUARD_REJECTED: '+str(error), file=sys.stderr)
        sys.exit(2)
