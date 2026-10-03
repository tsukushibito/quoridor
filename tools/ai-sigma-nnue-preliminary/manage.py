"""Bounded CPU0 management commands and readonly source inspection ledger."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

D = Path('research-data/ai-sigma/154-nnue-preliminary')
ledger = D / 'commands.json'


def identity(pid):
    try:
        raw = Path(f'/proc/{pid}/stat').read_text()
        return {'pid': pid, 'starttick': raw[raw.rfind(')')+2:].split()[19],
                'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except FileNotFoundError:
        return None


def main():
    lock = (D/'management.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    records = json.loads(ledger.read_text()) if ledger.exists() else []
    used = sum(x['wall_seconds'] for x in records)
    deadline = datetime.datetime.fromisoformat(json.loads((D/'intake.json').read_text())['newcommand_UTC'])
    assert datetime.datetime.now(datetime.timezone.utc) < deadline
    assert used < 120
    timeout = min(58, 120-used)
    argv = sys.argv[1:]
    env = dict(os.environ, BEADS_ACTOR='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418',
               PYTHONDONTWRITEBYTECODE='1', UV_NO_SYNC='1', UV_OFFLINE='1')
    os.sched_setaffinity(0, {0})
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.monotonic()
    outpath = D / f'command-{os.getpid()}.stdout.tmp'
    errpath = D / f'command-{os.getpid()}.stderr.tmp'
    with outpath.open('wb') as stdout, errpath.open('wb') as stderr:
        p = subprocess.Popen(argv, env=env, stdout=stdout, stderr=stderr)
        owned = identity(p.pid)
        sampled = 0
        cause = 'owned wait natural exit'
        while p.poll() is None:
            try:
                status = Path(f'/proc/{p.pid}/status').read_text()
                rss = next(int(x.split()[1])*1024 for x in status.splitlines() if x.startswith('VmRSS:'))
                sampled = max(sampled, rss)
                if rss > 448*1024**2 or time.monotonic()-t0 > timeout:
                    cause = 'own immediate-child guard/time kill; descendant status unknown'
                    p.kill()
                    break
            except (FileNotFoundError, StopIteration):
                pass
            time.sleep(.02)
        p.wait(timeout=1)
    out = outpath.read_bytes()
    err = errpath.read_bytes()
    r = {'command': argv, 'start_UTC': start, 'end_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'wall_seconds': time.monotonic()-t0, 'exit_code': p.returncode, 'manager': identity(os.getpid()),
         'child': owned, 'child_current_identity': identity(p.pid), 'owned_wait_complete': True,
         'stop': cause, 'sampled_immediate_child_RSS_bytes': sampled,
         'wait_ru_maxrss_bytes': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,
         'RSS_scope_limit': 'sample covers immediate child; not all descendant/current RSS assurance',
         'stdout_sha256': hashlib.sha256(out).hexdigest(), 'stderr': err.decode()[:3000],
         'stdout_file': str(outpath), 'stderr_file': str(errpath),
         'CPU_affinity': [0], 'formal_performance_measurement': False}
    records.append(r)
    ledger.write_text(json.dumps(records, indent=2)+'\n')
    sys.stdout.buffer.write(out)
    sys.stderr.buffer.write(err)
    sys.exit(p.returncode)


if __name__ == '__main__':
    main()
