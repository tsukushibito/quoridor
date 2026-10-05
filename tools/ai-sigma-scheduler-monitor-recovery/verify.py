import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import resource
import threading
import time
import uuid
import safe_state as s

ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma')
OUT=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY'
FIX=OUT/('fixtures-'+str(uuid.uuid4()));FIX.mkdir()
os.sched_setaffinity(0,{0});start=dt.datetime.now(dt.timezone.utc).isoformat();results=[]
binding={'thread_id':'01a0f6b5-b1bd-7752-b0bb-74a336e459a4'}
process={'pid':123456,'start_ticks':'12345','boot_id':'fixture-boot'}
valid={'binding':binding,'process':process,'phase':'running','owned':None}
logs=[]
def read(p):return s.read_bounded(p,lambda v:s.validate_state(v,binding,process),attempts=5,delay=.025,seconds=.3,log=logs.append)
def atomic(p,v):
 q=p.with_suffix('.tmp');q.write_text(json.dumps(v));os.replace(q,p)
p=FIX/'state.json';atomic(p,valid);assert read(p)==valid;results.append('valid-state')
p.unlink()
t=threading.Thread(target=lambda:(time.sleep(.015),atomic(p,valid)));t.start();assert read(p)==valid;t.join();results.append('transient-missing-bounded-recovery')
p.write_text('{broken')
t=threading.Thread(target=lambda:(time.sleep(.015),atomic(p,valid)));t.start();assert read(p)==valid;t.join();results.append('transient-json-bounded-recovery')
for name,content in [('persistent-missing',None),('persistent-corrupt','{broken'),('unknown-binding',json.dumps({**valid,'binding':{}})),('changed-identity',json.dumps({**valid,'process':{**process,'pid':123457}})),('unknown-owned-thread',json.dumps({**valid,'owned':{'thread_id':'foreign'}}))]:
 if content is None:p.unlink()
 else:p.write_text(content)
 begin=time.monotonic()
 try:read(p);raise AssertionError('must fail closed')
 except s.Unavailable:pass
 assert time.monotonic()-begin<.3
 results.append(name+'-fail-closed')
# Atomic replacement of an existing fixture preserves its path during reads.
atomic(p,valid);fail=[]
def writer():
 for _ in range(200):atomic(p,valid)
t=threading.Thread(target=writer);t.start()
for _ in range(200):
 try:json.loads(p.read_text())
 except Exception as e:fail.append(str(e))
t.join();assert not fail;results.append('200-existing-atomic-replaces-no-missing-observed')
signals=[]
observed={'pid':123456,'start_ticks':'12345','state':'S'}
s.signal_identity(process,observed,'fixture-boot',lambda x:signals.append(x));assert len(signals)==1
for changed,boot in [({**observed,'start_ticks':'12346'},'fixture-boot'),(observed,'other-boot'),(None,'fixture-boot')]:
 try:s.signal_identity(process,changed,boot,lambda x:signals.append(x));raise AssertionError('signal must be rejected')
 except s.Unavailable:pass
assert len(signals)==1;results.append('identity-pid-reuse-boot-unknown-signal-rejected')
ended=dt.datetime.now(dt.timezone.utc).isoformat();fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split();u=resource.getrusage(resource.RUSAGE_SELF)
r={'started_utc':start,'ended_utc':ended,'passed':len(results),'results':results,'failures':0,'read_events':logs,'pid':os.getpid(),'start_ticks':fields[19],'affinity':list(os.sched_getaffinity(0)),'maxrss_kib':u.ru_maxrss,'user_cpu_s':u.ru_utime,'sys_cpu_s':u.ru_stime,'live_state_fault_injection':False,'actual_signals_sent':0,'only_new_fixture_faults':True,'root_cause_proven':False,'atomic_fixture_no_missing_does_not_prove_live_FS_history':True}
(OUT/'verification.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'passed':r['passed'],'pid':r['pid'],'maxrss_kib':r['maxrss_kib'],'root_cause_proven':False}))
