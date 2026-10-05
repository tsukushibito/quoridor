"""Owned synchronous stop/save helpers. RAM is RSS, never address-space size."""
import datetime, hashlib, json, os, signal, subprocess, time
from pathlib import Path
R = Path.cwd()
T = R / 'tools/ai-sigma-formal-clock'
D = R / 'research-data/ai-sigma/161-formal-clock'
REPORT = R / 'docs/reports/ai-sigma-critic-formal-clock.md'
start = time.monotonic()
costs = []
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name, value):
    (D/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
def family_rss(pid):
    pending, seen, total = [pid], set(), 0
    while pending:
        n = pending.pop()
        if n in seen:
            continue
        seen.add(n)
        try:
            status = Path(f'/proc/{n}/status').read_text()
            total += int(next((x.split()[1] for x in status.splitlines() if x.startswith('VmRSS:')), '0'))*1024
            pending += [int(x) for x in Path(f'/proc/{n}/task/{n}/children').read_text().split()]
        except FileNotFoundError:
            pass
    return total
def run(args, env=None):
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime(2026,10,3,3,55,tzinfo=datetime.timezone.utc)
    begin = time.monotonic()
    p = subprocess.Popen(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
    peak = 0
    try:
        while True:
            # Includes parent Python plus only this command's descendants.
            rss = family_rss(os.getpid())
            peak = max(peak,rss)
            if rss > 448*1024*1024 or time.monotonic()-begin > 12:
                os.killpg(p.pid,signal.SIGTERM)
                raise RuntimeError('OWN_HELPER_RSS_OR_TIME_GUARD')
            try:
                out,err = p.communicate(timeout=.05)
                break
            except subprocess.TimeoutExpired:
                pass
        costs.append({'command':args,'wall_s':time.monotonic()-begin,'exit':p.returncode,'sampled_family_RSS_peak':peak,'instantaneous_peak_guarantee':False,'child_waited':True})
        if p.returncode:
            raise RuntimeError(str(args)+': '+out+err)
        return out
    finally:
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGTERM)
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL);p.wait()
run(['bash','scripts/dev/beads.sh','ready','--json'])
for issue in ['quoridor-4lc','quoridor-4lc.161']:
    x=json.loads(run(['bash','scripts/dev/beads.sh','show',issue,'--json']))[0]
    assert x['status']=='in_progress' and 'paused-by-user' not in x.get('labels',[])
    if issue.endswith('.161'):
        assert x['assignee']=='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'
mock=json.loads((D/'mock-r1-run.json').read_text())
assert mock['exit']==0 and mock['child_waited']
files=[p for base in [T,D] for p in base.rglob('*') if p.is_file() and p.name not in ['private.index','private.index.lock']]+[REPORT]
size=sum(p.stat().st_size for p in files)
st=json.loads((D/'intake.json').read_text())['storage']
assert size<2097152 and st['old_conservative_bytes']+st['158_current_bytes']+2097152<st['critic_guard_bytes']
sources=[*T.glob('*.cjs'),T/'finalize.py',REPORT,D/'instrument-schema.json']
save('science-source-stop.json',{'issue':'quoridor-4lc.161','UTC':now(),'scientific_source_write_stopped':True,'source_hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'mock_child_waited':True,'mock_exit':0,'tests':14,'Chrome_jobs':0,'new_NN_model_session_build_game_GPU_training_workers':0,'formal_ready':False,'NI_or_goal_achieved':False,'owned_bytes_before_cleanup':size,'Chrome_unperformed_reason':'chosen cheaper static cycle/selector; NN0 TID spin cannot prove real ORT tail','old_NN_backend_CPU_unknown':True,'next_single_proposal':'new same-core fixed1000 cycle finite real-provider capture under future allocation','current_absence_natural_allhost_guarantee':False,'management_attempt_r1':'RSS allocation mistakenly imposed as inherited RLIMIT_AS; Go reserve failure saved; not scientific failure','all_scientific_children_waited':True,'cleanup_helpers':'synchronous sampled RSS guard; no address-space cap'})
env=os.environ.copy();env['GIT_INDEX_FILE']=str(T/'private.index')
run(['git','read-tree','HEAD'],env)
paths=sorted({str(p.relative_to(R)) for p in files}|{str((D/'science-source-stop.json').relative_to(R))})
run(['git','add','--',*paths],env)
run(['git','commit','-m','research(161): preserve clock attribution prototype and typed management failures'],env)
commit=run(['git','rev-parse','HEAD']).strip()
entries=run(['git','ls-tree','-r','--name-only',commit,'--',str(T.relative_to(R)),str(D.relative_to(R)),str(REPORT.relative_to(R))]).splitlines()
checks=[]
for rel in entries:
    blob=run(['git','show',commit+':'+rel]).encode()
    assert blob==(R/rel).read_bytes(), rel
    checks.append({'path':rel,'bytes':len(blob),'SHA256':hashlib.sha256(blob).hexdigest()})
save('Git-restoration.json',{'UTC':now(),'data_Git':commit,'canonical_files':len(checks),'method':'Git blob stream matches current bytes; no raw copies','checks':checks})
notes='161: NN0 fixed1000ms cycle/402 main validated CP/411 planned public/500 bound proposal. 14 mock pass, 5 source-route binding checks. Real ORT tail/kernelCPU/mode unproven, formal_ready=false/Chrome0. report docs/reports/ai-sigma-critic-formal-clock.md; data Git '+commit+'. Source/scientific child stopped; query missing paths and management RLIMIT_AS Go reserve failure preserved. Coordinator acceptance/close pending.'
run(['bash','scripts/dev/beads.sh','update','quoridor-4lc.161','--append-notes',notes])
(D/'backup-sync.txt').write_text(run(['bash','scripts/dev/beads.sh','backup','sync']))
save('finalize-r2.json',{'UTC':now(),'exit':0,'phase':'stop Git restoration notes backup','wall_s':time.monotonic()-start,'commands':costs,'source_stop_sha256':hashlib.sha256((D/'science-source-stop.json').read_bytes()).hexdigest(),'data_Git':commit,'all_helpers_waited':True,'static_total_before_cleanup':'cheap source/read/admission and 1 mock; see intake/mock run; no exact whole-team CPU claim'})
print(json.dumps({'data_Git':commit,'canonical':len(checks),'wall_s':time.monotonic()-start,'backup_sync_exit':0}))
