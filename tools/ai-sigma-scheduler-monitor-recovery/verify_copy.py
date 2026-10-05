"""Exercise the actual copied read/stop functions in isolated namespaces."""
import ast
import datetime as dt
import json
import os
from pathlib import Path
import resource
import time
import uuid
import safe_state

ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma')
OUT=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY'
source=Path(__file__).with_name('watch.py')
tree=ast.parse(source.read_text())
names={'readstate','read_failure','matches','stop_owned'}
functions=ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names],type_ignores=[])
utc=dt.timezone.utc;start=dt.datetime.now(utc).isoformat();passed=[]
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
expected={'pid':123456,'start_ticks':'12345','boot_id':boot};binding={'thread_id':'01a0f6b5-b1bd-7752-b0bb-74a336e459a4'}
valid={'phase':'running','binding':binding,'process':expected,'owned':None}
for mode in ('valid-copy-read','missing-unknown-identity','missing-confirmed-owned-only'):
    case=OUT/('copy-fixture-'+mode+'-'+str(uuid.uuid4()));case.mkdir()
    if mode=='valid-copy-read':(case/'state.json').write_text(json.dumps(valid))
    signals=[];calls=[];kernel={'pid':expected['pid'],'start_ticks':'12345','state':'S'} if mode=='missing-confirmed-owned-only' else None
    def mock_signal(x):
        global kernel
        signals.append(x);kernel=None
        return {'mock_exact_owned_signal':True}
    scope={'OUT':case,'STATE':case,'ROOT':ROOT,'MAIN':Path('/workspaces/quoridor'),
           'CFG':ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json',
           'EXPECTED_PROCESS':expected,'EXPECTED_BINDING':binding,'LAST_GOOD':None,
           'safe_state':safe_state,'json':json,'Path':Path,'dt':dt,'UTC':utc,'time':time,
           'END':dt.datetime(2026,10,1,16,55,tzinfo=utc),'FINAL':dt.datetime(2026,10,1,16,58,tzinfo=utc),
           'now':lambda:dt.datetime.now(utc).isoformat(),'proc':lambda pid:kernel,
           'signal_exact_owned':mock_signal,
           'write':lambda name,v:(case/name).write_text(json.dumps(v,indent=2)+'\n'),
           'notify':lambda name,body:calls.append({'mock_notification':name}),
           'command':lambda args,timeout:calls.append({'unexpected_command':args})}
    exec(compile(functions,str(source),'exec'),scope)
    if mode=='valid-copy-read':assert scope['readstate']()==valid
    else:
        scope['stop_owned']('isolated persistent read failure')
        row=json.loads((case/'scheduler-end-stop.json').read_text())
        assert row['owned_turn_pending']=='unknown' and not row['scheduler_identity_alive']
        assert not any('unexpected_command' in x for x in calls)
        assert len(signals)==(1 if mode=='missing-confirmed-owned-only' else 0)
    passed.append(mode)
u=resource.getrusage(resource.RUSAGE_SELF);fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
d={'started_utc':start,'ended_utc':dt.datetime.now(utc).isoformat(),'passed':len(passed),'cases':passed,
   'copied_functions_tested':sorted(names),'actual_signals_sent':0,'live_state_injection':False,
   'pid':os.getpid(),'start_ticks':fields[19],'maxrss_kib':u.ru_maxrss,'user_cpu_s':u.ru_utime,'sys_cpu_s':u.ru_stime,
   'affinity':list(os.sched_getaffinity(0)),'unknown_ownership_not_cleared_or_inferred_zero':True}
(OUT/'copy-verification.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'passed':len(passed),'pid':os.getpid(),'actual_signals_sent':0}))
