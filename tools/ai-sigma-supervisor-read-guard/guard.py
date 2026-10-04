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
import selectors
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

class ReadFailed(Rejected):
    """A bounded metadata attempt failed; only explicit transient causes retry."""
    def __init__(self, message, transient=False):
        super().__init__(message)
        self.transient = transient

GOAL = 'quoridor-4lc'
SELF = 'quoridor-4lc.40'
REPORT_RESERVE = 30
OPERATION_BEGIN = dt.datetime(2026, 10, 4, 5, 55, 50, tzinfo=UTC)
OPERATION_END = dt.datetime(2026, 10, 4, 7, 50, 50, tzinfo=UTC)
# New runs only: pipes are transient memory, not retained wrapper transcripts.
RAW_PIPE_CAP = 4 * 1024**2
SELECTED_CAP = 64 * 1024
RUN_CAP = 384 * 1024
FAILURE_RESERVE = 8 * 1024
RUN_FORECAST = 512 * 1024
COMMAND_CAP = 24
NOTE_CAP = 1024
_FIELD_REQUEST = None

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
    encoded = (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    if len(encoded) > SELECTED_CAP:
        raise Rejected('selected_record_overflow: use bounded inspect field/offset')
    if BASE in path.parents:
        run_root = BASE / path.relative_to(BASE).parts[0]
        actual = allocated_bytes([run_root])
        # Charge the temporary file before replacement, including 4KiB rounding.
        forecast = ((len(encoded) + 4095) // 4096) * 4096 + 4096
        ceiling = RUN_CAP if path.name.startswith('failure') or path.name == 'terminal-refusal.json' else RUN_CAP - FAILURE_RESERVE
        if actual + forecast > ceiling:
            raise Rejected('run_retention_cap: no further command; failure reserve retained')
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_bytes(encoded)
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
            'read_start_planning_at_utc': (start+dt.timedelta(seconds=90)).isoformat(),
            'read_finish_planning_at_utc': (start+dt.timedelta(seconds=120)).isoformat(),
            'turn_deadline_utc': (start+dt.timedelta(seconds=180)).isoformat(),
            'initial_mapping_limit': 'Initial UTC-to-monotonic mapping assumes no prior wall-clock jump; future/backwards boot/start is rejected.'}

def age_now(bound, wall=None, mono=None):
    wall = wall or utc_now()
    mono = time.monotonic() if mono is None else mono
    if mono < bound['mapped_start_monotonic']:
        raise Rejected('Monotonic clock went backwards')
    return max((wall-parse_utc(bound['started_at'])).total_seconds(),
               mono-bound['mapped_start_monotonic'])

def admit(bound, phase, wall=None, mono=None, required_seconds=0):
    age = age_now(bound, wall, mono)
    # 90/120 are planning checkpoints, not a permanent ban on research reads.
    remaining = min(180-age, (OPERATION_END-(wall or utc_now())).total_seconds())
    reserve = REPORT_RESERVE if phase in ('read_start', 'read_finish') else 0
    if remaining <= required_seconds+reserve:
        raise Rejected(f'{phase} insufficient remaining time ({remaining:.6f}s; need {required_seconds+reserve}s)')
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

def allocated_bytes(roots):
    seen = set(); total = 0
    for root in roots:
        stack = [root]
        while stack:
            p = stack.pop()
            try:
                stat = p.lstat(); key = (stat.st_dev, stat.st_ino)
                if key in seen:
                    continue
                seen.add(key); total += stat.st_blocks * 512
                if p.is_dir() and not p.is_symlink():
                    stack.extend(p.iterdir())
            except FileNotFoundError:
                continue
            except OSError as error:
                raise Rejected('Storage allocation unknown: ' + str(p)) from error
    return total


def owned_storage_bytes():
    # Same steward ownership as the existing monitor; supervisor history is separate.
    return allocated_bytes((ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92', ROOT / '.artifacts/ai-sigma/continuation-20261001/scheduler', RUNTIME, ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-EXPERIMENT-POLICY-85', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-CONTRACT-IMPROVEMENT-88', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-READ-GUARD', ROOT / 'tools/ai-sigma-supervisor-read-guard', ROOT / 'tools/ai-sigma-scheduler-monitor-recovery', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY', ROOT / 'tools/ai-sigma-scheduler-deadline-update', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-DEADLINE-UPDATE', ROOT / 'tools/ai-sigma-supervisor-role-review', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-ROLE-REVIEW', ROOT / 'tools/ai-sigma-critical-roles-v2', ROOT / '.artifacts/ai-sigma/continuation-20261001/SIGMA-CRITICAL-ROLES-V2', ROOT / 'tools/ai-sigma-experiment-policy', ROOT / 'docs/reports/ai-sigma-steward-experiment-policy.md', ROOT / 'docs/reports/ai-sigma-steward-critical-roles-v2.md', ROOT / 'docs/reports/ai-sigma-steward-supervisor-role-review.md', ROOT / 'docs/reports/ai-sigma-steward-deadline-20261002.md', ROOT / 'docs/reports/ai-sigma-steward-scheduler-live.md', ROOT / 'docs/reports/ai-sigma-steward-supervisor-read-guard.md', ROOT / 'docs/reports/ai-sigma-steward-scheduler-recovery.md'))


def supervisor_storage_bytes():
    if BASE.is_symlink() or not BASE.is_dir():
        raise Rejected('Supervisor storage ownership unknown')
    frame_roots = []
    for directory in BASE.iterdir():
        if directory.is_symlink():
            raise Rejected('Supervisor storage ownership unknown: symlink')
        binding_path = directory / 'read-guard/binding.json'
        try:
            saved = json.loads(binding_path.read_text())
            start = parse_utc(saved['started_at'])
            if saved.get('thread_id') != THREAD:
                raise Rejected('Supervisor storage owner unknown')
            if start >= OPERATION_BEGIN:
                if start > utc_now():
                    raise Rejected('Supervisor storage start is in the future')
                frame_roots.append(directory)
        except (FileNotFoundError, KeyError, ValueError) as error:
            # Legacy unbound evidence remains held and charged; a new unknown run refuses.
            if directory.stat().st_mtime >= OPERATION_BEGIN.timestamp():
                raise Rejected('Current supervisor storage ownership unknown') from error
    held = allocated_bytes([BASE])
    current = allocated_bytes(frame_roots)
    return held, current


def check_storage(forecast_bytes=RUN_FORECAST):
    steward = owned_storage_bytes()
    held, current = supervisor_storage_bytes()
    if steward + forecast_bytes > 112 * 1024**2:
        raise Rejected('Steward allocated/forecast guard; no command launched')
    if current + forecast_bytes > 32 * 1024**2:
        raise Rejected('Current supervisor reservation/forecast guard; no command launched')
    return {'steward_allocated_bytes': steward,
            'supervisor_held_bytes': held, 'supervisor_current_frame_bytes': current,
            'supervisor_historical_held_bytes': held-current,
            'forecast_bytes': forecast_bytes, 'additional_reservation_bytes': 0,
            'historical_parent_charge_released': False}

def select_text(text, cap, tail=False, offset=None):
    raw = str(text or '').encode()
    start = max(0, len(raw)-cap) if tail else 0
    if offset is not None:
        start = min(offset, len(raw))
    end = min(len(raw), start+cap)
    # Select complete UTF-8 codepoints; byte ranges refer to original bytes.
    while start < end and raw[start] & 0xC0 == 0x80:
        start += 1
    while end < len(raw) and end > start and raw[end] & 0xC0 == 0x80:
        end -= 1
    return raw[start:end].decode(), {'source_bytes': len(raw),
        'source_sha256': hashlib.sha256(raw).hexdigest(), 'range': [start, end],
        'complete': start == 0 and end == len(raw),
        'missing': None if start == 0 and end == len(raw) else 'bounded_field_evidence',
        'additional_read': 'inspect --issue ID --field notes|description --offset BYTE'}


def select_stdout(value, args):
    if len(args) > 1 and args[1] == str(MAIN/'scripts/dev/beads.sh') and isinstance(value, list):
        is_show = 'show' in args
        result = []
        fields = ('id', 'title', 'status', 'assignee', 'labels', 'updated_at',
                  'created_at', 'started_at', 'parent', 'dependency_count', 'dependent_count')
        for row in value:
            if not isinstance(row, dict):
                raise ReadFailed('Unexpected wrapper issue schema')
            selected = {key: row[key] for key in fields if key in row}
            selected['dependencies'] = dependency_summary(row.get('dependencies'))
            coverage = {}
            if is_show:
                for field, cap, tail in (('description', 3072, False), ('notes', 1024, True)):
                    request = _FIELD_REQUEST if _FIELD_REQUEST and _FIELD_REQUEST[0] == field else None
                    selected[field], coverage[field] = select_text(row.get(field),
                        8192 if request else cap, tail=tail and not request,
                        offset=request[1] if request else None)
            coverage['omitted_fields'] = sorted(set(row)-set(selected)-{'description', 'notes', 'dependencies'})
            selected['_selection'] = coverage
            result.append(selected)
        return result
    if isinstance(value, dict) and 'text' in value and 'path' in value:
        text, coverage = select_text(value['text'], 8192,
            offset=_FIELD_REQUEST[1] if _FIELD_REQUEST and _FIELD_REQUEST[0] == 'document' else None)
        return {**value, 'text': text, '_selection': coverage}
    return value


def retain_stdout(raw, args, directory, complete=True):
    source = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'complete_pipe': complete, 'full_wrapper_stdout_retained': False}
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        # Non-JSON bookkeeping output is also bounded and explicitly scoped.
        parsed, coverage = select_text(raw.decode(errors='replace'), 1024)
        selected = {'text': parsed, '_selection': coverage}
    else:
        selected = select_stdout(parsed, args)
    encoded = json.dumps(selected, ensure_ascii=False, separators=(',', ':')).encode()
    if len(encoded) > SELECTED_CAP:
        raise ReadFailed('selected_output_overflow: required evidence exceeds cap; use bounded inspect')
    digest = hashlib.sha256(encoded).hexdigest()
    blob = directory / ('selection-'+digest+'.json')
    if not blob.exists():
        write(blob, selected)
    return selected, {**source, 'selection': str(blob), 'selected_bytes': len(encoded),
                      'selected_sha256': digest, 'same_selection_reuses_reference': True}


def run_child(args, path, bound, phase='read', background=(), timeout=12, return_value=False):
    admit(bound, 'read_start' if phase == 'read' else 'finish', required_seconds=timeout+2)
    storage = check_storage()
    directory = path.parent
    # A persistent counter includes inspect, retries, authorization and finish.
    ledger = directory/'command-count.json'
    count = json.loads(ledger.read_text())['count'] if ledger.exists() else 0
    if count >= COMMAND_CAP:
        raise Rejected('run_command_cap: no command launched')
    if BASE in path.parents and allocated_bytes([BASE/path.relative_to(BASE).parts[0]]) + SELECTED_CAP + 16*1024 > RUN_CAP - FAILURE_RESERVE:
        raise Rejected('run_retention_cap: next spawn blocked')
    write(ledger, {'count': count+1, 'limit': COMMAND_CAP})
    admit(bound, 'read_start' if phase == 'read' else 'finish', required_seconds=timeout+2)
    limit = 180-REPORT_RESERVE if phase == 'read' else 180
    started = stamp(); started['storage_accounting'] = storage
    peak = 0; cause = None
    # AS is intentionally inherited without imposing 1GiB; Go/cgo needs virtual reserve.
    raw = {'stdout': bytearray(), 'stderr': bytearray()}
    hashes = {key: hashlib.sha256() for key in raw}; sizes = {key: 0 for key in raw}
    selector = selectors.DefaultSelector()
    child = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env={**os.environ, **ENV}, start_new_session=True)
    try:
        for key, pipe in (('stdout', child.stdout), ('stderr', child.stderr)):
            os.set_blocking(pipe.fileno(), False); selector.register(pipe, selectors.EVENT_READ, key)
        ident = proc(child.pid)
        command_deadline = time.monotonic() + timeout
        try:
            while selector.get_map() or child.poll() is None:
                for event, _ in selector.select(.02):
                    chunk = os.read(event.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(event.fileobj); continue
                    key = event.data; sizes[key] += len(chunk); hashes[key].update(chunk)
                    room = RAW_PIPE_CAP-len(raw[key]); raw[key].extend(chunk[:max(0, room)])
                    if sum(sizes.values()) > RAW_PIPE_CAP and cause is None:
                        cause = 'raw_pipe_overflow'; cleanup_group(child)
                peak = max(peak, sampled_rss(child.pid, background))
                if child.poll() is None and not cause:
                    if peak >= 1024**3: cause = 'sampled_combined_RSS_guard'
                    elif time.monotonic() >= command_deadline or age_now(bound) >= limit-2 or utc_now() >= OPERATION_END-dt.timedelta(seconds=2): cause = 'timeout/deadline'
                    if cause: cleanup_group(child)
            child.wait()
        except BaseException as error:
            cause = 'operator/interruption: '+type(error).__name__
            cleanup_group(child)
        finally:
            if child.poll() is None:
                cleanup_group(child)
    finally:
        selector.close(); child.stdout.close(); child.stderr.close()
    finished = stamp()
    row = {'command': args, 'started': started, 'finished': finished, 'child': ident,
           'exit_code': child.returncode, 'cause': cause, 'reaped': True,
           'sampled_combined_RSS_peak_bytes': peak, 'sample_interval_seconds': 0.02,
           'instant_RSS_peak_not_guaranteed': True, 'phase': phase,
           'age_started_seconds': age_now(bound, parse_utc(started['utc']), started['monotonic']),
           'age_finished_seconds': age_now(bound, parse_utc(finished['utc']), finished['monotonic']),
           'stdout_evidence': {'bytes': sizes['stdout'], 'sha256': hashes['stdout'].hexdigest(),
                               'complete_pipe': not bool(cause)},
           'stderr_evidence': {'bytes': sizes['stderr'], 'sha256': hashes['stderr'].hexdigest(),
                               'excerpt': bytes(raw['stderr'][:1024]).decode(errors='replace')},
           'output_limits': {'raw_pipe_bytes': RAW_PIPE_CAP, 'selection_bytes': SELECTED_CAP,
                             'run_allocated_bytes': RUN_CAP, 'commands': COMMAND_CAP}}
    value = None
    if not cause and child.returncode == 0:
        try:
            value, row['stdout_evidence'] = retain_stdout(bytes(raw['stdout']), args, directory)
        except (Rejected, ReadFailed) as error:
            cause = str(error); row['cause'] = cause
    write(path, row)
    if cause or child.returncode:
        error = bytes(raw['stderr'][-4096:]).decode(errors='replace')
        transient = (cause == 'timeout/deadline' and age_now(bound) < limit-2) or (not cause and any(x in error.lower() for x in ('database is locked', 'resource temporarily unavailable', 'connection reset', 'temporarily unavailable', 'connection refused')))
        raise ReadFailed('Owned command failed; child reaped: '+str(cause or error), transient=transient and phase == 'read')
    admit(bound, 'read_finish' if phase == 'read' else 'finish')
    if phase != 'read' and not return_value:
        return row
    if isinstance(value, dict) and 'text' in value and not ('path' in value):
        raise ReadFailed('invalid_metadata_json: required structured evidence absent')
    return value

def live_owned(run, turn, prior):
    if prior:
        admit(prior, 'finish')
    state = json.loads((RUNTIME/'state.json').read_text())
    b = state.get('binding') or {}
    if state.get('phase') != 'running' or state.get('recovery_required') or b.get('thread_id') != THREAD or b.get('dispatch_issue') != 'quoridor-4lc.40':
        raise Rejected('Runtime binding unavailable/unresolved')
    expected = state.get('process'); observed = proc(expected['pid']) if expected else None
    if not observed or observed['state'] == 'Z' or observed['start_ticks'] != str(expected['start_ticks']) or expected.get('boot_id') != boot_id():
        raise Rejected('Scheduler identity absent/changed')
    bound = binding(state.get('owned'), run, turn, prior)
    admit(bound, 'finish')
    return bound, state

def read_retry(args, directory, name, bound, background=(), owner_check=None, attempts=2):
    """At most two attempts, with the same owned clock; hard refusals never retry."""
    for attempt in range(attempts):
        if owner_check:
            owner_check()
        admit(bound, 'read_start', required_seconds=14)
        try:
            return run_child(args, directory/(name+f'-attempt-{attempt+1}.json'), bound, background=background)
        except ReadFailed as error:
            if not error.transient or attempt+1 == attempts:
                raise

DEPENDENCY_REFERENCE_FIELDS = ('id', 'issue_id', 'depends_on_id', 'type',
                               'dependency_type', 'status', 'assignee')


def dependency_summary(dependencies):
    """Keep relation references, never embedded issue history or nested graphs."""
    result = []
    for item in dependencies or []:
        if isinstance(item, str):
            result.append({'id': item})
        elif isinstance(item, dict):
            reference = {key: item[key] for key in DEPENDENCY_REFERENCE_FIELDS
                         if key in item and isinstance(item[key], (str, int, bool, type(None)))}
            if 'labels' in item:
                reference['labels'] = [label for label in item['labels'] or []
                                       if isinstance(label, str)]
            result.append(reference)
    return result


def issue_summary(issues):
    return [{'id': x.get('id'), 'status': x.get('status'), 'assignee': x.get('assignee'),
             'title': x.get('title'), 'updated_at': x.get('updated_at'),
             'description': x.get('description'), '_selection': x.get('_selection'),
             'labels': x.get('labels') or [], 'dependencies': dependency_summary(x.get('dependencies')),
             'dependency_count': x.get('dependency_count'),
             'notes_tail': str(x.get('notes') or '')[-1200:]} for x in issues]

def require_unpaused(issues):
    core = {x.get('id'): x for x in issues}
    if any(i not in core for i in (GOAL, SELF)):
        raise Rejected('Goal/self authorization snapshot missing')
    if any('paused-by-user' in (core[i].get('labels') or []) or core[i].get('status') not in ('open', 'in_progress') for i in (GOAL, SELF)):
        raise Rejected('Goal/self paused or unavailable; do not retry/bypass')
    if core[SELF].get('assignee') != 'codex:'+THREAD or core[SELF].get('status') != 'in_progress':
        raise Rejected('Self owner/status unknown; no retry or claim')

def select_current(issues, ready=(), limit=8):
    rows = [x for x in issues if x.get('id', '').startswith(GOAL+'.') and x.get('status') in ('open', 'in_progress', 'blocked') and x.get('id') != SELF]
    # Keep the live operation and ready work visible; stale in_progress labels
    # must not displace newer contracts merely because they have an assignee.
    rows.sort(key=lambda x: str(x.get('updated_at') or ''), reverse=True)
    rows.sort(key=lambda x: 0 if x.get('id') == GOAL+'.92' else 1 if x.get('id') in ready else 2)
    return list(dict.fromkeys(x['id'] for x in rows))[:limit]

def observe(directory, run, turn, refresh=False):
    prior_path = directory/'binding.json'
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else None
    bound, state = live_owned(run, turn, prior)
    write(prior_path, bound)
    write(directory/'storage-policy.json', {'version': 'bounded-records-v1',
        'guard_run_allocated_cap': RUN_CAP, 'total_run_cap': RUN_FORECAST,
        'failure_reserved_bytes': FAILURE_RESERVE, 'command_cap': COMMAND_CAP,
        'raw_pipe_cap': RAW_PIPE_CAP, 'selected_record_cap': SELECTED_CAP,
        'notes_increment_cap': NOTE_CAP, 'external_report_limit_bytes': 16384})
    if (directory/'observation.json').exists() and not refresh:
        return {'cached': True, 'observation': str(directory/'observation.json'), 'binding': bound}
    background = [state['process']]
    monitor = ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE/monitor-process.json'
    if monitor.exists():
        background.append(json.loads(monitor.read_text())['process'])
    prefix = ['bash', str(MAIN/'scripts/dev/beads.sh')]
    values = {}
    begin = stamp()
    token = str(time.monotonic_ns())
    def owner_check():
        current, _ = live_owned(run, bound['turn_id'], bound)
        assert current == bound
    def read(name, args):
        return read_retry(args, directory, token+'-'+name, bound, background, owner_check)
    core = read('core', prefix+['show', GOAL, SELF, '--json'])
    write(directory/'authorization.json', {'at': stamp(), 'issues': issue_summary(core)})
    require_unpaused(core)
    values['ready'] = read('ready', prefix+['ready', '--json'])
    current = read('current', prefix+['list', '--parent', GOAL, '--status', 'open,in_progress,blocked', '--sort', 'updated', '--limit', '24', '--json'])
    # Current subcontracts may be grandchildren (for example the present .88.1).
    for parent in select_current(current, limit=3):
        current += read('children-'+parent, prefix+['list', '--parent', parent, '--status', 'open,in_progress,blocked', '--limit', '8', '--json'])
    selected = select_current(current, {x.get('id') for x in values['ready']})
    values['issues'] = core + (read('selected', prefix+['show', *selected, '--json']) if selected else [])
    values['sessions'] = read('sessions', ['bash', str(MAIN/'scripts/dev/research-team.sh'), 'status'])
    admit(bound, 'read_finish')
    issues = values['issues']
    if not isinstance(issues, list):
        raise Rejected('Unexpected issues shape; retain command raw')
    summary = issue_summary(issues)
    require_unpaused(issues)
    result = {'run_id': run, 'turn_id': bound['turn_id'], 'binding': bound, 'started': begin,
              'finished': stamp(), 'ready_ids': [x.get('id') for x in values['ready']], 'issues': summary,
              'sessions': values['sessions'], 'scheduler_snapshot': state,
              'background_identities_for_RSS': background,
              'pause_observed': False, 'current_issue_ids': [x.get('id') for x in current],
              'discovery_limits': {'direct': 24, 'nested_parents': 3, 'per_nested': 8, 'detail': 8},
              'not_all_history_or_descendants_scanned': True,
              'read_command_count': len(list(directory.glob(token+'-*-attempt-*.json'))),
              'scripted_path_only': True, 'whole_turn_compliance_verified': False,
              'side_DB_cache_writes_not_quantified': True,
              'old_deviations_32games_goal_not_attained_preserved': True}
    if (directory/'observation.json').exists():
        write(directory/('observation-'+token+'.json'), result)
    write(directory/'observation.json', result)
    return result

def inspect(directory, run, turn, issue_ids=(), files=()):
    """Additional relevant readonly checks, sharing the original turn budget."""
    prior = json.loads((directory/'binding.json').read_text())
    bound, state = live_owned(run, turn, prior)
    if len(issue_ids) > 8 or len(files) > 4:
        raise Rejected('Bound additional evidence request to eight issues/four documents')
    if any(not i.startswith(GOAL+'.') or not all(c.isalnum() or c in '.-' for c in i) for i in issue_ids):
        raise Rejected('Additional issue outside goal namespace')
    background = [state['process']]
    check = lambda: live_owned(run, bound['turn_id'], bound)
    prefix = ['bash', str(MAIN/'scripts/dev/beads.sh')]
    token = 'inspect-'+str(time.monotonic_ns())
    core = read_retry(prefix+['show', GOAL, SELF, '--json'], directory, token+'-core', bound, background, check)
    require_unpaused(core)
    result = {'at': stamp(), 'binding': bound, 'issues': [], 'documents': []}
    if issue_ids:
        rows = read_retry(prefix+['show', *issue_ids, '--json'], directory, token+'-issues', bound, background, check)
        if any('paused-by-user' in (x.get('labels') or []) for x in rows):
            raise Rejected('Selected issue paused; no further checks')
        result['issues'] = [{**row, 'dependencies': dependency_summary(row.get('dependencies'))}
                            for row in rows]
    for name in files:
        path = Path(name).resolve()
        allowed = [base/sub for base in (ROOT, MAIN) for sub in ('docs/design', 'docs/reports', '.artifacts/ai-sigma/continuation-20261001')]
        if not any(base in path.parents for base in allowed):
            raise Rejected('Document outside research evidence namespaces')
        code = "import pathlib,json,sys;p=pathlib.Path(sys.argv[1]);f=p.open('rb');b=f.read(131073);f.close();assert len(b)<=131072,'Document too large';print(json.dumps({'path':str(p),'text':b.decode()}))"
        result['documents'].append(read_retry([sys.executable, '-B', '-c', code, str(path)], directory, token+'-file-'+str(len(result['documents'])), bound, background, check))
    write(directory/(token+'.json'), result)
    return result

def validate_note(note):
    if len(note.encode()) > NOTE_CAP:
        raise Rejected('notes_increment_overflow: save independent judgment in bounded report; append short time/judgment/evidence reference')


def finish(directory, run, turn, note):
    # Bounded current pause/owner check is bookkeeping, sharing the owned clock.
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
    validate_note(note)
    admit(bound, 'finish', required_seconds=36)
    authorization = directory/('finish-authorization-'+str(time.monotonic_ns())+'.json')
    authorization_rows = run_child(['bash', str(MAIN/'scripts/dev/beads.sh'), 'show', GOAL, SELF, '--json'],
              authorization, bound, phase='finish', timeout=10,
              background=observation['background_identities_for_RSS'], return_value=True)
    require_unpaused(authorization_rows)
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
    global _FIELD_REQUEST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('observe', 'inspect', 'finish'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--turn-id')
    parser.add_argument('--refresh', action='store_true', help='Refresh relevant snapshot using original owned clock')
    parser.add_argument('--issue', action='append', default=[])
    parser.add_argument('--file', action='append', default=[])
    parser.add_argument('--field', choices=('description', 'notes', 'document'))
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--note', default='監督の保存済みバッチ観測。旧逸脱/欠測/目標未達を保持、正常なら通知0。')
    args = parser.parse_args()
    if args.offset < 0 or (args.field and args.operation != 'inspect'):
        raise Rejected('Invalid bounded field request')
    _FIELD_REQUEST = (args.field, args.offset) if args.field else None
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
        if (directory/'terminal-refusal.json').exists():
            raise Rejected('prior_terminal_refusal: no retry/output accumulation in same run')
        try:
            if args.operation == 'observe':
                result = observe(directory, run, args.turn_id, args.refresh)
            elif args.operation == 'inspect':
                result = inspect(directory, run, args.turn_id, args.issue, args.file)
            else:
                result = finish(directory, run, args.turn_id, args.note)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as error:
            write(directory/'terminal-refusal.json', {'utc': utc_now().isoformat(),
                'operation': args.operation, 'error': str(error)[:1024],
                'no_foreign_process_or_turn_stopped': True, 'blind_retry': False})
            raise

if __name__ == '__main__':
    try:
        main()
    except (Rejected, OSError, ValueError, subprocess.SubprocessError) as error:
        print('READ_GUARD_REJECTED: '+str(error), file=sys.stderr)
        sys.exit(2)
