"""Finite CPU2 job manager; owns only its child process group."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

D=Path('research-data/ai-sigma/frame14-learning')
ROOT=Path('/workspaces/quoridor')
GUARD=1879048192


def utc():return datetime.datetime.now(datetime.timezone.utc)


def write(p,j):p.write_text(json.dumps(j,indent=2)+'\n')


def proc(pid):
    try:
        p=Path('/proc')/str(pid);s=(p/'stat').read_text();a=s[s.rfind(')')+2:].split()
        return {'pid':int(pid),'ppid':int(a[1]),'pgrp':int(a[2]),'tick':a[19],
                'RSS':int(a[21])*os.sysconf('SC_PAGE_SIZE'),'cmd':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),
                'affinity':sorted(os.sched_getaffinity(int(pid)))}
    except (OSError,ValueError,IndexError):return None


def current():return [r for p in Path('/proc').iterdir() if p.name.isdigit() and (r:=proc(p.name))]


def family(table,pid):
    ids={pid}
    while True:
        expanded=ids|{r['pid'] for r in table if r['ppid'] in ids}
        if expanded==ids:return [r for r in table if r['pid'] in ids]
        ids=expanded


def state(id):
    p=subprocess.run(['bash','scripts/dev/beads.sh','show',id,'--json'],capture_output=True,text=True,timeout=15,check=True)
    j=json.loads(p.stdout);j=j[0] if isinstance(j,list) else j
    return {k:j.get(k) for k in ['id','status','assignee','labels']}


def main(a):
    os.sched_setaffinity(0,{2})
    job=D/'jobs'/a.id
    if job.exists():raise ValueError('job ID exists; success is never overwritten')
    prior=[json.loads(p.read_text()) for p in (D/'jobs').glob('*/process.json')] if (D/'jobs').exists() else []
    spent=sum(p['wall_seconds'] for p in prior if p['kind']==a.kind)
    charged=sum(p.get('samples_charged',0) for p in prior)
    if spent+a.seconds>(900 if a.kind=='heavy' else 1200) or charged+a.samples>5000000:
        raise ValueError('cumulative job/sample budget')
    deadline=datetime.datetime.fromisoformat(a.stop.replace('Z','+00:00'))
    latest=datetime.datetime.fromisoformat(a.new.replace('Z','+00:00'))
    if utc()>=latest or utc()+datetime.timedelta(seconds=a.seconds+30)>deadline:
        raise ValueError('newcommand or hardstop window unavailable')
    own=state('quoridor-4lc.195');goal=state('quoridor-4lc')
    if own['assignee']!='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418' or own['status']!='in_progress' or any('paused-by-user' in (j['labels'] or []) for j in [own,goal]):
        raise ValueError('owner/pause')
    table=current();active=[];services=[]
    for r in table:
        cmd=r['cmd']
        if r['pid']==os.getpid() or not cmd or cmd.startswith('/bin/bash -c ') or 'manage_frame14.py' in cmd:continue
        script=next((x for x in cmd.split() if x.endswith(('.py','.cjs'))), '')
        # An argument list containing runner.py is not a running model job.
        # The generation owner's small Git metadata helper is explicitly allowed.
        if script.endswith('/save_git.py'):services.append(r);continue
        if 'scheduler.py run' in cmd or '/watch.py ' in cmd:services.append(r)
        elif ('tools/ai-sigma-frame14-teachers/' in cmd or 'tools/ai-sigma-manygame-generation/provider.py' in cmd or 'tools/ai-sigma-manygame-generation/worker.cjs' in cmd
              or ('nnue-training/' in cmd and ('train.py' in cmd or 'frame14.py evaluate' in cmd or 'test_contrast.py evaluate' in cmd)) or 'sigma-native-bridge' in cmd):active.append(r)
    if active:raise ValueError('external science/owner active: '+str([(r['pid'],r['tick'],r['cmd'][:120]) for r in active]))
    scheduler=json.loads((ROOT/'.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
    # CPU0 owned observer is separate from this CPU2 single-thread job; save current binding.
    research_rss=sum(r['RSS'] for r in services+active)
    if research_rss+2*1024**3+1024**3>8*1024**3:raise ValueError('parent RAM forecast')
    storage=json.loads((D/'storage-admission.json').read_text())
    if storage['forecast_B']>=58720256 or not storage['transfer_confirmed']:raise ValueError('storage admission')
    job.mkdir(parents=True)
    write(job/'admission.json',{'UTC':utc().isoformat(),'own':own,'goal':goal,'active':active,'services':services,
            'scheduler_owned':scheduler.get('owned'),'next_observe':scheduler.get('next_at'),'CPU':[2],'threads':1,'RAM_guard':GUARD,
            'parent_RSS_forecast':research_rss+3*1024**3,'storage':storage,'command':a.command,'sample_upper':a.samples,'newscience':a.new,'stop':a.stop})
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
    start=time.monotonic();peak=0;reason='completed';descendants={}
    with (job/'stdout.txt').open('wb') as stdout,(job/'stderr.txt').open('wb') as stderr:
        child=subprocess.Popen(a.command,stdout=stdout,stderr=stderr,env=env,start_new_session=True)
        identity=proc(child.pid);write(job/'owned-current.json',{'UTC':utc().isoformat(),'identity':identity,'kind':a.kind})
        while child.poll() is None:
            f=family(current(),child.pid)
            for r in f:descendants[(r['pid'],r['tick'])]=r
            rss=sum(r['RSS'] for r in f)+proc(os.getpid())['RSS'];peak=max(peak,rss)
            if rss>=GUARD or time.monotonic()-start>=a.seconds or utc()>=deadline:
                reason='RAM_GUARD' if rss>=GUARD else 'HARD_TIMEOUT'
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
                break
            time.sleep(.05)
        code=child.wait()
    remaining=[r for (pid,tick) in descendants if (r:=proc(pid)) and r['tick']==tick]
    if remaining:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        # No new work if any family identity remains unreaped.
        time.sleep(.1)
        remaining=[r for (pid,tick) in descendants if (r:=proc(pid)) and r['tick']==tick]
    actual=a.samples
    if a.result and Path(a.result).exists():
        result=json.loads(Path(a.result).read_text());actual=result.get('all_samples',result.get('samples',a.samples))
    record={'id':a.id,'kind':a.kind,'UTC':utc().isoformat(),'identity':identity,'command':a.command,'wall_seconds':time.monotonic()-start,
            'peak_family_RSS':peak,'exit':code,'reason':reason,'child_waited':True,'remaining':remaining,
            'current_exact_identity_absent':not (identity and (r:=proc(child.pid)) and r['tick']==identity['tick']),
            'samples_charged':actual,'sample_cap':a.samples,'CPU':[2],'GPU':0}
    write(job/'process.json',record);print(json.dumps(record))
    if code or remaining or actual>a.samples:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--kind',choices=['static','heavy'],required=True)
    p.add_argument('--seconds',type=float,default=120);p.add_argument('--samples',type=int,default=0)
    p.add_argument('--result');p.add_argument('--new',default='2026-10-04T02:45:00Z');p.add_argument('--stop',default='2026-10-04T02:50:00Z')
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.command and a.command[0]=='--':a.command=a.command[1:]
    if not a.command or not 0<a.seconds<=120:raise ValueError('command/hard120')
    main(a)
