"""Own one bounded static checker child and save its identity, RSS and outcome."""
import datetime
import hashlib
import json
import os
import pathlib
import resource
import subprocess
import sys
import time

BASE = pathlib.Path('research-data/ai-sigma/frame10-gap-sampling')
GUARD = 448*1024*1024


def identity(pid):
    try:
        raw = pathlib.Path(f'/proc/{pid}/stat').read_text()
        return {'pid': pid, 'starttick': raw[raw.rfind(')')+2:].split()[19],
                'boot_id': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except FileNotFoundError:
        return None


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (GUARD, GUARD))
    resource.setrlimit(resource.RLIMIT_CPU, (55, 55))
    os.sched_setaffinity(0, {0})


paths = ['tools/ai-sigma-frame10-gap-sampling/verify.py',
         'tools/ai-sigma-frame10-gap-sampling/run-controlled.py',
         str(BASE/'recommended-seeds.json'),
         'research-data/ai-sigma/119-diverse-prefix/preregister.json']
before = {p: digest(p) for p in paths}
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
t0 = time.monotonic()
cmd = [sys.executable, '-B', 'tools/ai-sigma-frame10-gap-sampling/verify.py']
child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limits)
child_id = identity(child.pid)
peak_sample_rss = 0
stop = 'natural child exit observed by owned wait'
while child.poll() is None:
    try:
        status = pathlib.Path(f'/proc/{child.pid}/status').read_text()
        rss = next(int(line.split()[1])*1024 for line in status.splitlines() if line.startswith('VmRSS:'))
        peak_sample_rss = max(peak_sample_rss, rss)
        if rss > GUARD or time.monotonic()-t0 > 58:
            stop = 'own child guard/time stop'
            child.kill()
            break
    except (FileNotFoundError, StopIteration):
        pass
    time.sleep(.01)
out, err = child.communicate(timeout=1)
ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
result = {'issue': 'quoridor-4lc.148', 'run': 'static-r1', 'command': cmd,
          'start_UTC': started, 'end_UTC': ended, 'wall_seconds': time.monotonic()-t0,
          'manager_identity': identity(os.getpid()), 'child_identity': child_id,
          'child_exit_code': child.returncode, 'owned_wait_complete': True,
          'current_child_identity': identity(child.pid), 'remaining_unknown_owned_children': 0,
          'stop': stop, 'current_absence_is_not_all_host_or_all_period_guarantee': True,
          'CPU_affinity': [0], 'logical_CPUs': 1, 'RAM_guard_bytes': GUARD,
          'sampled_child_peak_RSS_bytes': peak_sample_rss,
          'wait_child_ru_maxrss_bytes': usage.ru_maxrss*1024,
          'child_CPU_seconds': usage.ru_utime+usage.ru_stime,
          'input_source_sha256_before': before, 'input_source_sha256_after': {p: digest(p) for p in paths},
          'stdout': out.decode(), 'stderr': err.decode(), 'NN': 0, 'Chrome': 0, 'game': 0}
(BASE/'static-run.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
sys.exit(child.returncode)
