#!/usr/bin/env python3
"""Bounded local research child job; no task state or shared environment updates."""
import argparse, datetime, hashlib, json, os, signal, subprocess, sys, time, resource
from pathlib import Path

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def allocated(root):
    total = 0
    if root.exists():
        for base, dirs, files in os.walk(root, followlinks=False):
            for name in files:
                p = Path(base)/name
                if not p.is_symlink():
                    try: total += p.stat().st_blocks*512
                    except FileNotFoundError: pass
    return total

def processes():
    rows={}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                s=(p/'stat').read_text(); a=s[s.rfind(')')+2:].split()
                rows[int(p.name)]={'ppid':int(a[1]),'pgid':int(a[2]),'rss':int(a[21])*os.sysconf('SC_PAGE_SIZE'), 'ticks':int(a[11])+int(a[12]),'start_tick':int(a[19]),'cpu':int(a[36]),'state':a[0]}
            except (OSError,IndexError,ValueError): pass
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--id',required=True);ap.add_argument('--experiment',default='SIGMA-RULE-FEATURE-PARITY');ap.add_argument('--cpus',default='2,4');ap.add_argument('--timeout',type=float,default=600);ap.add_argument('command',nargs=argparse.REMAINDER);args=ap.parse_args(); os.sched_setaffinity(0,{int(x) for x in args.cpus.split(',')})
    cmd=args.command[1:] if args.command[:1]==['--'] else args.command
    root=Path.cwd(); run=root/'.artifacts/ai-sigma/runs'/args.experiment; info=json.loads((run/'contract-run.json').read_text())
    deadline=datetime.datetime.fromisoformat(info['deadline_utc']).timestamp(); timeout=min(args.timeout,deadline-time.time());assert timeout>0
    paths=[root/'.artifacts/ai-sigma',root/'node_modules',root/'apps/web/node_modules',root/'packages/engine-bridge/node_modules',root/'packages/engine-bridge/wasm',root/'apps/web/dist',Path('/home/vscode/.cache/inference/research/ai-sigma/npm')]
    bpath=run/'storage-baseline.json'
    if not bpath.exists(): bpath.write_text(json.dumps({str(p):allocated(p) for p in paths}))
    baseline=json.loads(bpath.read_text()); sizes=lambda:{str(p):allocated(p) for p in paths}
    before=sizes(); increment=lambda s:sum(max(0,v-baseline[k]) for k,v in s.items())
    env=dict(os.environ);env.update({'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','CARGO_BUILD_JOBS':'2','CARGO_TARGET_DIR':str(root/'.artifacts/ai-sigma/build/native')})
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['Cargo.lock','package-lock.json','tests/fixtures/ai/native-search.json']}
    if Path(cmd[0]).is_file():hashes[cmd[0]]=hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest()
    record={'job_id':args.id,'issue':info.get('issue','quoridor-4lc.5'),'experiment':args.experiment,'start_utc':utc(),'cwd':str(root),'command':cmd,'affinity':args.cpus,'timeout_seconds':timeout,'hashes':hashes,'seed':1979,'limits':info['limits'],'checkpoint':None,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'monitor_affinity':sorted(os.sched_getaffinity(0)),'storage_before':before,'storage_increment_before':increment(before)}
    log=run/(args.id+'.log'); meta=run/(args.id+'.json'); samples=run/(args.id+'.resources.jsonl')
    with log.open('w') as stream:
        job_wall_start=time.monotonic(); usage_start=resource.getrusage(resource.RUSAGE_CHILDREN); cpu_before=Path('/proc/stat').read_text(); system_before=processes()
        p=subprocess.Popen(['taskset','-c',args.cpus,*cmd],env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        record.update(pid=p.pid,pgid=p.pid,log=str(log));meta.write_text(json.dumps(record,indent=2));known={p.pid:None};peak_rss=0;peak_storage=increment(before);last_disk=0;reason='exit';stop=False;start=time.monotonic()
        def interrupted(sig,frame):
            nonlocal stop,reason
            stop=True;reason='signal_'+str(sig)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        monitor_error=None
        try:
            with samples.open('w') as f:
                while p.poll() is None:
                    rows=processes();own={i for i,s in rows.items() if s['pgid']==p.pid or (i in known and s['start_tick']==known[i])}
                    changed=True
                    while changed:
                        new={i for i,s in rows.items() if s['ppid'] in own};changed=not new.issubset(own);own|=new
                    known.update({i:rows[i]['start_tick'] for i in own if i in rows}); active={i:rows[i] for i in own if i in rows};rss=sum(s['rss'] for s in active.values())+rows.get(os.getpid(),{}).get('rss',0);peak_rss=max(peak_rss,rss)
                    f.write(json.dumps({'utc':utc(),'processes':active,'rss_sum':rss})+'\n');f.flush()
                    if time.monotonic()-last_disk>2:
                        current_sizes=sizes();peak_storage=max(peak_storage,increment(current_sizes));last_disk=time.monotonic()
                        if sum(current_sizes.values())>2.75*1024**3:stop=True;reason='owned_storage_guard'
                    if rss>3.5*1024**3:stop=True;reason='ram_guard'
                    if peak_storage>info.get('storage_limit_bytes',4*1024**3)*.875:stop=True;reason='storage_guard'
                    if time.monotonic()-start>timeout:stop=True;reason='timeout'
                    if stop:
                        os.killpg(p.pid,signal.SIGTERM)
                        try:p.wait(timeout=5)
                        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                        break
                    time.sleep(.1)
        except BaseException as exc:
            monitor_error=repr(exc);reason='monitor_error'
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL);p.wait()
        rc=p.wait();rows=processes();known.update({i:s['start_tick'] for i,s in rows.items() if s['pgid']==p.pid});live=[i for i in known if i in rows and rows[i]['start_tick']==known[i] and rows[i]['state']!='Z']
        for i in live:
            try:os.kill(i,signal.SIGTERM)
            except ProcessLookupError:pass
        if live:time.sleep(.2)
        rows=processes();remaining=[i for i in live if i in rows and rows[i]['start_tick']==known[i] and rows[i]['state']!='Z']
        for i in remaining:
            try:os.kill(i,signal.SIGKILL)
            except ProcessLookupError:pass
        usage=resource.getrusage(resource.RUSAGE_CHILDREN); record.update(wall_seconds=time.monotonic()-job_wall_start,user_seconds=usage.ru_utime-usage_start.ru_utime,sys_seconds=usage.ru_stime-usage_start.ru_stime,maxrss_kib=usage.ru_maxrss,proc_stat_before=cpu_before,proc_stat_after=Path('/proc/stat').read_text(),system_processes_before=system_before,system_processes_after=processes())
        if remaining:time.sleep(.2)
        final_rows=processes();record['remaining_final']=[i for i in known if i in final_rows and final_rows[i]['start_tick']==known[i] and final_rows[i]['state']!='Z']
        after=sizes();peak_storage=max(peak_storage,increment(after));record.update(monitor_error=monitor_error,end_utc=utc(),exit_code=rc,exit_signal=-rc if rc<0 else None,reason=reason,observed_child_pids=sorted(known),child_exit_note='direct child reaped; short-lived descendants exits recorded by time aggregate, individual exit codes unavailable',rss_sample_peak=peak_rss,storage_after=after,storage_increment_after=increment(after),storage_increment_peak=peak_storage,cleanup_signalled=live,remaining_after_term=remaining)
        meta.write_text(json.dumps(record,indent=2));print(json.dumps({'job':args.id,'exit':rc,'reason':reason,'rss_peak':peak_rss,'storage_increment':increment(after)}));return 1 if monitor_error else (rc if rc>=0 else 128-rc)
if __name__=='__main__':sys.exit(main())
