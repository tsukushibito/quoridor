"""CPU8 ownership/admission, 30s timeout, current RSS guard and child wait."""
import datetime, hashlib, json, os, subprocess, time
from pathlib import Path

D = Path('research-data/ai-sigma/186-value-game-diagnostic')
def save(n, v):
    (D/n).write_text(json.dumps(v, indent=2)+'\n')
def proc(pid):
    p = Path('/proc')/str(pid)
    st = (p/'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=int(pid), tick=st[19], RSS=int(st[21])*os.sysconf('SC_PAGE_SIZE'), ppid=int(st[1]))

assert os.sched_getaffinity(0) == {8}
assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime(2026,10,3,12,29,tzinfo=datetime.timezone.utc)
pr = json.loads((D/'preregister.json').read_text())
assert hashlib.sha256(Path('tools/ai-sigma-value-game-diagnostic/evaluate.py').read_bytes()).hexdigest() == pr['eval_source_SHA256']
own = {os.getpid()}
cur = os.getpid()
while cur > 1:
    cur = proc(cur)['ppid']
    own.add(cur)
old = Path('research-data/ai-sigma/185-manygame-runtime-preparation')
assert json.loads((old/'handoff-stop.json').read_text())['owned_children_reaped']
identities = []
for path in (old/'runs').glob('*/process.json'):
    for item in json.loads(path.read_text()).get('tracked', []):
        try:
            same = proc(item['pid'])['tick'] == str(item['tick'])
        except FileNotFoundError:
            same = False
        identities.append(dict(pid=item['pid'], tick=item['tick'], current_same=same))
assert not any(x['current_same'] for x in identities)
active, service = [], []
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name) in own:
        continue
    try:
        cmd = (p/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        if ('ai-sigma' in cmd or 'research-team' in cmd) and any(s in cmd for s in ['python', 'node', 'faithful-native']):
            r=proc(p.name);r['cmd']=cmd[:500]
            (service if 'scheduler.py run' in cmd or '/watch.py ' in cmd else active).append(r)
    except (FileNotFoundError, ProcessLookupError):
        pass
scheduler = json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
save('admission.json',dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),CPU=[8],active=active,services=service,scheduler_owned=scheduler.get('owned'),next_observe=scheduler.get('next_at'),previous185identities=identities,RAM_self_guard=939524096, aggregate_forecast_bytes=1073741824+1073741824+536870912+sum(r['RSS'] for r in active+service)))
assert not active, 'UNKNOWN_CURRENT_OWNER_OR_JOB'
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','UV_NO_SYNC':'1','UV_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
command=['/home/vscode/.cache/inference/envs/quoridor-training/bin/python','-B','tools/ai-sigma-value-game-diagnostic/evaluate.py']
started=time.monotonic();peak=0;reason=None
with (D/'stdout.txt').open('w') as out,(D/'stderr.txt').open('w') as err:
    child=subprocess.Popen(command,env=env,stdout=out,stderr=err)
    identity=proc(child.pid)
    save('owned-current.json',dict(identity=identity,command=command,UTC=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    while child.poll() is None:
        try:peak=max(peak,proc(child.pid)['RSS'])
        except FileNotFoundError:pass
        if peak>939524096:reason='RSS_GUARD'
        if time.monotonic()-started>30:reason='TIME_GUARD'
        if reason:
            child.terminate()
            try:child.wait(timeout=1)
            except subprocess.TimeoutExpired:child.kill()
            break
        time.sleep(.02)
    code=child.wait()
save('process-stop.json',dict(identity=identity,command=command,exit=code,reason=reason,wall_seconds=time.monotonic()-started,peak_RSS_bytes=peak,waited=True,current_PID_absent=not Path('/proc/'+str(child.pid)).exists(),CPU_affinity=[8],GPU_calls=0,training=0,UTC=datetime.datetime.now(datetime.timezone.utc).isoformat()))
print(json.dumps(dict(exit=code,reason=reason,wall_seconds=time.monotonic()-started,peak_RSS_bytes=peak)))
