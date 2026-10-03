"""Owned scheduler observation/stop guard; no research execution or delegation."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma')
MAIN=Path('/workspaces/quoridor')
import argparse
import safe_state
parser=argparse.ArgumentParser()
parser.add_argument('--run-dir',required=True)
parser.add_argument('--expectations',required=True)
args=parser.parse_args()
OUT=Path(args.run_dir).resolve()
ALLOWED=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92'
if ALLOWED not in OUT.parents:raise ValueError('Run output outside owned recovery namespace')
OUT.mkdir(parents=True,exist_ok=True)
EXPECTED=json.loads(Path(args.expectations).read_text())
EXPECTED_PROCESS=EXPECTED['process']
EXPECTED_BINDING=EXPECTED['binding']
EVENT_EPOCH=EXPECTED['operation_epoch_utc']
LAST_GOOD=None
STATE=MAIN/'.artifacts/research-team/scheduler-sigma-continuation-20261001'
CFG=ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json'
UTC=dt.timezone.utc
END=dt.datetime(2026,10,3,8,10,21,tzinfo=UTC)
FINAL=dt.datetime(2026,10,3,8,13,21,tzinfo=UTC)
HEAVY=dt.datetime(2026,10,3,8,5,21,tzinfo=UTC)
os.sched_setaffinity(0,{0})
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
os.environ.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
START=dt.datetime.now(UTC)
stopping=False
signal.signal(signal.SIGTERM,lambda *_:globals().__setitem__('stopping',True))
signal.signal(signal.SIGINT,lambda *_:globals().__setitem__('stopping',True))

def now(): return dt.datetime.now(UTC).isoformat()
def write(name,v):
    p=OUT/name; tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)
def read_failure(event):
    with (OUT/'bounded-read-events.jsonl').open('a') as f:
        f.write(json.dumps({'observed_utc':now(),**event},ensure_ascii=False)+'\n')
def readstate():
    global LAST_GOOD
    for path,expected in EXPECTED['input_hashes'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise safe_state.Unavailable('Deadline input hash changed: '+path)
    value=safe_state.read_bounded(STATE/'state.json',
          lambda v:safe_state.validate_state(v,EXPECTED_BINDING,EXPECTED_PROCESS),log=read_failure)
    LAST_GOOD=value
    return value
def proc(pid):
    try:
        p=Path('/proc')/str(pid); f=(p/'stat').read_text().rsplit(')',1)[1].split()
        rss=int(f[21])*os.sysconf('SC_PAGE_SIZE')
        return {'pid':pid,'start_ticks':f[19],'state':f[0],'rss_bytes':rss,
                'cpu_ticks':int(f[11])+int(f[12]),'affinity':list(os.sched_getaffinity(pid))}
    except (OSError,ValueError,IndexError): return None
def matches(expected,observed):
    return bool(expected and observed and expected['pid']==observed['pid']
                and str(expected['start_ticks'])==observed['start_ticks'] and observed['state']!='Z')
def command(args,timeout=40):
    remaining=(FINAL-dt.datetime.now(UTC)).total_seconds()
    if remaining<=0: raise TimeoutError('Final handling deadline')
    child=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                           start_new_session=True)
    ident=proc(child.pid)
    try: out,err=child.communicate(timeout=min(timeout,remaining))
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGTERM)
        try: out,err=child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate(timeout=3)
        row={'command':args,'at':now(),'process':ident,'exit_code':child.returncode,
             'stdout':out,'stderr':err,'timed_out':True,'reaped':True}
        with (OUT/'monitor-commands.jsonl').open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
        raise TimeoutError('Owned command timed out; child reaped')
    row={'command':args,'at':now(),'process':ident,'exit_code':child.returncode,
         'stdout':out,'stderr':err,'reaped':True}
    with (OUT/'monitor-commands.jsonl').open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return row
def notify(name,body):
    p=OUT/(name+'.md');p.write_text(body+'\n')
    try:
        for issue in ('quoridor-4lc','quoridor-4lc.92'):
            r=command(['bash',str(MAIN/'scripts/dev/beads.sh'),'show',issue,'--json'],12)
            if r['exit_code']: raise RuntimeError('Issue read failed')
            v=json.loads(r['stdout']);v=v[0] if isinstance(v,list) else v
            if v['status'] not in ('open','in_progress') or 'paused-by-user' in (v.get('labels') or []):
                write(name+'-delivery.json',{'at':now(),'sent':False,'reason':'issue not authorized/paused'});return
        note=command(['bash',str(MAIN/'scripts/dev/beads.sh'),'update','quoridor-4lc.92',
                      '--if-assignee','codex:01a0f31d-99ee-7d63-b162-bc1a59c457c6',
                      '--if-status','in_progress','--append-notes',
                      'Owned metadata monitor '+name+' evidence '+str(p)+
                      '; history/owned scheduler scope only, semantic success and external NN stop not certified.'],12)
        if note['exit_code']: raise RuntimeError('Own issue update failed')
        backup=command(['bash',str(MAIN/'scripts/dev/beads.sh'),'backup','sync'],20)
        if backup['exit_code']: raise RuntimeError('Backup failed')
        receipt=command([sys.executable,'-B',str(OUT.parent/'report.py'),str(p)],40)
        write(name+'-delivery.json',receipt)
    except Exception as e:
        write(name+'-delivery.json',{'at':now(),'sent_or_accepted_unconfirmed':True,'error':str(e),
                                   'blind_retry':False})
def storage_size():
    seen=set();total=0
    for root in (OUT.parent,CFG.parent,STATE,
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-EXPERIMENT-POLICY-85',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-CONTRACT-IMPROVEMENT-88',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-READ-GUARD',
                 ROOT/'tools/ai-sigma-supervisor-read-guard',ROOT/'tools/ai-sigma-scheduler-monitor-recovery',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY',
                 ROOT/'tools/ai-sigma-scheduler-deadline-update',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-DEADLINE-UPDATE',
                 ROOT/'tools/ai-sigma-supervisor-role-review',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-ROLE-REVIEW',
                 ROOT/'tools/ai-sigma-critical-roles-v2',
                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-CRITICAL-ROLES-V2',
                 ROOT/'tools/ai-sigma-experiment-policy',
                 ROOT/'docs/reports/ai-sigma-steward-experiment-policy.md',
                 ROOT/'docs/reports/ai-sigma-steward-critical-roles-v2.md',
                 ROOT/'docs/reports/ai-sigma-steward-supervisor-role-review.md',
                 ROOT/'docs/reports/ai-sigma-steward-deadline-20261002.md',
                 ROOT/'docs/reports/ai-sigma-steward-scheduler-live.md',
                 ROOT/'docs/reports/ai-sigma-steward-supervisor-read-guard.md',
                 ROOT/'docs/reports/ai-sigma-steward-scheduler-recovery.md'):
        stack=[root]
        while stack:
            p=stack.pop()
            try:
                s=p.lstat();key=(s.st_dev,s.st_ino)
                if key not in seen: seen.add(key);total+=s.st_blocks*512
                if p.is_dir() and not p.is_symlink(): stack.extend(p.iterdir())
            except FileNotFoundError: pass
    return total
def signal_exact_owned(expected):
    fd=os.pidfd_open(expected['pid'])
    try:
        observed=proc(expected['pid'])
        if not matches(expected,observed):raise safe_state.Unavailable('PID identity changed after pidfd open')
        signal.pidfd_send_signal(fd,signal.SIGUSR1)
    finally:os.close(fd)
    return {'signal':'SIGUSR1','process':expected,'scope':'only stored owned scheduler, which interrupts its exact owned turn'}
def stop_owned(reason):
    state=None;read_error=None
    try:state=readstate()
    except safe_state.Unavailable as e:read_error=str(e)
    observed=proc(EXPECTED_PROCESS['pid'])
    if matches(EXPECTED_PROCESS,observed):
        if state is not None:
            result=command([sys.executable,'-B',str(OUT.parent/'scheduler.py'),'stop',
                            '--state-dir',str(STATE),'--interrupt-owned-turn'],50)
        else:
            # A missing/unknown state must never select some newer process from it.
            result=safe_state.signal_identity(EXPECTED_PROCESS,observed,
                   Path('/proc/sys/kernel/random/boot_id').read_text().strip(),signal_exact_owned)
            until=min(time.monotonic()+45,time.monotonic()+max(0,(FINAL-dt.datetime.now(UTC)).total_seconds()))
            while matches(EXPECTED_PROCESS,proc(EXPECTED_PROCESS['pid'])) and time.monotonic()<until:time.sleep(.05)
    elif state is not None and state.get('owned') and dt.datetime.now(UTC)>=END:
        result=command([sys.executable,'-B',str(OUT.parent/'scheduler.py'),'run',
                        '--state-dir',str(STATE),'--config',str(CFG)],60)
    else:result={'command_not_needed':True,'reason':'stored scheduler not alive; retain unknown/pending ownership'}
    final=None
    try:final=readstate()
    except safe_state.Unavailable as e:read_error=str(e)
    alive=matches(EXPECTED_PROCESS,proc(EXPECTED_PROCESS['pid']))
    pending=bool(final.get('owned')) if final is not None else 'unknown'
    row={'at':now(),'reason':reason,'command_result':result,'state':final,
         'read_error':read_error,'last_valid_state':LAST_GOOD if final is None else None,
         'scheduler_identity_alive':alive,'owned_turn_pending':pending,
         'external_NN_processes_stopped':False,'scope':'stored owned scheduler/turn only',
         'read_failure_not_hidden':True,'no_automatic_restart_or_blind_send':True}
    write('scheduler-end-stop.json',row)
    notify('scheduler-end-report','quoridor-4lc.92 deadline scheduler停止。\n'+
           '詳細 '+str(OUT/'scheduler-end-stop.json')+'。owned_turn_pending='+str(pending)+
           '、scheduler_identity_alive='+str(alive)+'。原因/読取欠測を保持、外部NN停止認定0。')

boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
myself=proc(os.getpid());myself['boot_id']=boot
write('monitor-process.json',{'started_utc':START.isoformat(),'process':myself,
       'command':[sys.executable,'-B',str(Path(__file__).resolve())],
       'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'operation_epoch_utc':EVENT_EPOCH,'recovery_issue':'quoridor-4lc.92','owned_scheduler_expected':EXPECTED_PROCESS,
       'expected_input_hashes':EXPECTED['input_hashes'],'deadline_utc':END.isoformat(),'cleanup_deadline_utc':FINAL.isoformat(),
       'scope':'bounded state/events; first new epoch ownedturn report; exact owned scheduler deadline/guard stop',
       'ram_guard_bytes':1024**3,'allocated_guard_bytes':112*1024**2,
       'sampled_not_kernel_enforced':True,'no_NN_build_download_delete_delegation':True})
heavy_notified=False
first=None;finished=None;first_reported=False;old_last=None;peak=0;storage_peak=0;samples=0;last_error=None
reason='unknown';exit_code=0
try:
    while True:
        if stopping: reason='monitor operator stop';stop_owned(reason);break
        if dt.datetime.now(UTC)>=END: reason='2026-10-03 08:10:21 owned operation deadline';stop_owned(reason);break
        if dt.datetime.now(UTC)>=HEAVY and not heavy_notified:
            heavy_notified=True
            notify('heavy-job-stop-notice','quoridor-4lc.92 / 08:05:21UTC到達。新しい重いjobの開始を止め、各ownerが自己jobを回収。監督08:10:21/monitor08:13:21/証拠08:15:21。外部NN停止は認定しない。')
        state=readstate();owned=state.get('owned');p=state.get('process')
        # New bounded-record runs only. Existing historical evidence is untouched.
        bounded_run_bytes=None
        if owned:
            run_root=ROOT/'.artifacts/ai-sigma/continuation-20261001/supervisor'/owned['run_id']
            policy=run_root/'read-guard/storage-policy.json'
            if policy.exists() and json.loads(policy.read_text()).get('version')=='bounded-records-v1':
                seen=set();bounded_run_bytes=0;stack=[run_root]
                while stack:
                    item=stack.pop()
                    try:stat=item.lstat()
                    except FileNotFoundError:continue  # atomic recorder replacement
                    key=(stat.st_dev,stat.st_ino)
                    if key in seen:continue
                    seen.add(key);bounded_run_bytes+=stat.st_blocks*512
                    if item.is_dir() and not item.is_symlink():stack.extend(item.iterdir())
                if bounded_run_bytes>512*1024:
                    reason='bounded supervisor run output guard';stop_owned(reason);break
        observed=proc(p['pid']) if p else None
        members=[proc(os.getpid())]
        if matches(p,observed):
            stack=[p['pid']];visited=set()
            while stack and len(visited)<32:
                pid=stack.pop()
                if pid in visited:continue
                visited.add(pid);item=proc(pid)
                if item:members.append(item)
                try:stack.extend(int(x) for x in Path(f'/proc/{pid}/task/{pid}/children').read_text().split())
                except OSError:pass
        rss=sum(x['rss_bytes'] for x in members if x);peak=max(peak,rss);samples+=1
        allocated=storage_size();storage_peak=max(storage_peak,allocated)
        last=state.get('last_result');event=(last or {}).get('event')
        if last!=old_last:
            with (OUT/'monitor-events.jsonl').open('a') as f:
                f.write(json.dumps({'observed_utc':now(),'last_result':last,'owned':owned,
                                   'scheduler_process':p,'sampled_rss_bytes':rss,'allocated_bytes':allocated},ensure_ascii=False)+'\n')
            old_last=last
        # Read only this owned runtime's bounded event log, not sessions or shared caches.
        events=STATE/'events.jsonl'
        event_text=safe_state.read_bounded(events,parse=lambda text:text,log=read_failure)
        if event_text:
            for line in event_text.splitlines():
                try:e=json.loads(line)
                except ValueError:continue
                if e.get('event')=='dispatched' and e.get('at','')>=EVENT_EPOCH and first is None:first=e
                if first and e.get('event')=='owned_turn_finished' and e.get('turn_id')==first['turn_id']:finished=e
        write('monitor-observation.json',{'at':now(),'process':myself,'scheduler_process':p,
               'scheduler_identity_alive':matches(p,observed),'owned':owned,'last_result':last,
               'first_dispatched':first,'first_owned_turn_finished':finished,
               'sampled_owned_process_rss_peak_bytes':peak,'own_scope_allocated_peak_bytes':storage_peak,
               'sample_count':samples,'all_team_pid_zero_claimed':False,
               'bounded_supervisor_run_allocated_bytes':bounded_run_bytes,
               'inspection_semantic_success_independently_verified':False})
        if finished and not first_reported:
            first_reported=True
            write('first-live-turn.json',{'observed_utc':now(),'dispatched':first,'finished':finished,
                  'history_completion_only':True,'semantic_success_pending_independent_critic':True,
                  'source_events':str(events),'source_events_sha256':hashlib.sha256(events.read_bytes()).hexdigest()})
            notify('first-live-turn-report','quoridor-4lc.92 / 初回実監督turn観測。\n'+
                   'dispatched='+json.dumps(first,ensure_ascii=False)+'\nfinished='+json.dumps(finished,ensure_ascii=False)+
                   '\n過去枠のactive_limit skipとは別のframe10 dispatch。App Server履歴上の完了のみ、点検内容/全面稼働成功は独立critic待ち。'+
                   '\n詳細 '+str(OUT/'first-live-turn.json')+' / '+str(OUT/'monitor-observation.json')+
                   '。schedulerは2026-10-03 08:10:21UTCまで継続、.92停止責任保持。旧逸脱/欠測/32局/goal未達維持。')
        if rss>=1024**3 or allocated>=112*1024**2:
            reason='sampled owner RAM/storage guard';stop_owned(reason);break
        if state.get('phase')=='stopped' and not matches(p,observed):
            reason='scheduler stopped before deadline'
            write('scheduler-end-stop.json',{'at':now(),'reason':reason,'state':state,
                  'owned_turn_pending':bool(owned),'external_NN_processes_stopped':False})
            notify('scheduler-end-report','quoridor-4lc.92 / scheduler早期停止を観測。詳細 '+
                   str(OUT/'scheduler-end-stop.json')+'。owned turn未確認なら正確IDで回収要。外部NN停止認定0。');break
        time.sleep(10)
except Exception as e:
    reason='monitor abnormal exit';last_error=str(e);exit_code=1
    write('monitor-failure.json',{'at':now(),'error':last_error,'retain_state_and_events':True})
    try:stop_owned(reason)
    except Exception as stop_error:write('monitor-stop-unconfirmed.json',{'at':now(),'error':str(stop_error)})
finally:
    u=resource.getrusage(resource.RUSAGE_SELF);c=resource.getrusage(resource.RUSAGE_CHILDREN)
    write('monitor-ended.json',{'started_utc':START.isoformat(),'ended_utc':now(),'process':myself,
          'reason':reason,'error':last_error,'exit_code_if_normal':exit_code,
          'self_user_cpu_s':u.ru_utime,'self_sys_cpu_s':u.ru_stime,'self_maxrss_kib':u.ru_maxrss,
          'child_user_cpu_s':c.ru_utime,'child_sys_cpu_s':c.ru_stime,'child_maxrss_kib':c.ru_maxrss,
          'sampled_combined_rss_peak_bytes':peak,'allocated_peak_bytes':storage_peak,
          'no_child_command_left_running':True,'own_process_exits_after_this_record':True,
          'all_research_stopped_claimed':False})
sys.exit(exit_code)
