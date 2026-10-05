"""Owned deadline transition; command and identity evidence, no research execution."""
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
import uuid

ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma')
MAIN=Path('/workspaces/quoridor')
OUT=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-DEADLINE-UPDATE'
TOOLS=ROOT/'tools/ai-sigma-scheduler-deadline-update'
CFG=ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json'
STATE=MAIN/'.artifacts/research-team/scheduler-sigma-continuation-20261001'
OLD=ROOT/'tools/ai-sigma-scheduler-monitor-recovery'
OLD_RUN=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY/live-daa5b686-937b-4522-953d-83993dfaf9e4'
END='2026-10-02T00:55:00Z'
os.sched_setaffinity(0,{0})
os.environ.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
OUT.mkdir(parents=True,exist_ok=True)
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):
 p=OUT/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def proc(pid):
 try:
  p=Path('/proc')/str(pid);s=(p/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':pid,'start_ticks':s[19],'state':s[0],'rss_bytes':int(s[21])*os.sysconf('SC_PAGE_SIZE'),'affinity':list(os.sched_getaffinity(pid)),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
 except OSError:return None
def alive(expected):
 p=proc(expected['pid'])
 return bool(p and p['state']!='Z' and all(str(p[k])==str(expected[k]) for k in ('pid','start_ticks','boot_id')))
def state():return json.loads((STATE/'state.json').read_text())
def command(args,seconds=30):
 p=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 ident=proc(p.pid)
 try:o,e=p.communicate(timeout=seconds)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:o,e=p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);o,e=p.communicate(timeout=3)
  raise RuntimeError('Owned short command timeout/reaped')
 row={'at':now(),'command':args,'identity':ident,'exit_code':p.returncode,'stdout':o,'stderr':e,'reaped':True}
 with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 if p.returncode:raise RuntimeError(e or o)
 return json.loads(o)
def wrapper(action):
 args=['bash',str(MAIN/'scripts/dev/research-scheduler.sh'),action,'--state-dir',str(STATE)]
 if action in ('validate','start','run'):args+=['--config',str(CFG)]
 return command(args)
def prepare():
 if (OUT/'before.json').exists():raise RuntimeError('Before evidence already exists; no overwrite')
 sources=[CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md',OLD/'watch.py',OLD/'safe_state.py']
 rows=[]
 for i,p in enumerate(sources):
  data=p.read_bytes();dest=OUT/f'before-{i}-{p.name}';dest.write_bytes(data)
  rows.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'copy':str(dest)})
 st=state();monitor=json.loads((OLD_RUN/'monitor-process.json').read_text())['process']
 assert st['binding']['thread_id']=='01a0f6b5-b1bd-7752-b0bb-74a336e459a4' and st['phase']=='running'
 assert alive(st['process']) and alive(monitor)
 refs=[ROOT/'docs/design/ai-sigma-contract-steward-deadline-20261002.md',ROOT/'docs/design/ai-sigma-continuation-20261001.md',ROOT/'docs/design/ai-sigma-contract-steward-scheduler-recovery.md',ROOT/'docs/reports/ai-sigma-steward-scheduler-recovery.md',MAIN/'scripts/dev/research-scheduler.py',MAIN/'.artifacts/research-team/registry.json',ROOT/'.agents/research-team/common.md']+list((ROOT/'.agents/research-team/roles').glob('*.md'))
 write('before.json',{'at':now(),'operator':proc(os.getpid()),'edited_or_copy_sources':rows,'immutable_refs':[{'path':str(p),'sha256':sha(p)} for p in refs],'state':st,'scheduler_observed':proc(st['process']['pid']),'monitor':monitor,'monitor_observed':proc(monitor['pid']),'old_events_sha256':sha(STATE/'events.jsonl')})
 for p in [CFG,CFG.parent/'contract.json']:
  v=json.loads(p.read_text());assert v['end_at']=='2026-10-01T16:55:00Z';v['end_at']=END;p.write_text(json.dumps(v,indent=2)+'\n')
 prompt=CFG.parent/'prompt.md';s=prompt.read_text();old='16:40以降は保存観測から終了責任/次枠契約の有無を統括へ一度通知。scheduler/watchの16:55停止はsteward .38、目標枠17:00。'
 assert s.count(old)==1;s=s.replace(old,'2026-10-02 00:40UTC以降は保存観測から終了責任/次枠契約の有無を統括へ一度通知。schedulerの00:55UTC停止/watchの00:58UTC回収はsteward .38/.44/.53、目標枠01:00UTC。');prompt.write_text(s)
 doc=ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md'
 s=doc.read_text().replace('終了16:55UTC。','終了2026-10-02 00:55UTC（ユーザー明示期限変更、.53補足）。')
 s+='\n期限補足（quoridor-4lc.53、継続正本版2）: 重job00:50UTC、監督00:55UTC、monitor回収00:58UTC、枠終了01:00UTC。期間以外の権限/90・120・180秒gate/周期1200秒/閾値2は維持。旧個別期限と失敗は遡及延長しない。全期間運用成功や新対局許可を意味しない。\n';doc.write_text(s)
 s=(OLD/'watch.py').read_text()
 replacements={"SIGMA-SCHEDULER-RECOVERY'":"SIGMA-DEADLINE-UPDATE'",'dt.datetime(2026,10,1,16,55,tzinfo=UTC)':'dt.datetime(2026,10,2,0,55,tzinfo=UTC)','dt.datetime(2026,10,1,16,58,tzinfo=UTC)':'dt.datetime(2026,10,2,0,58,tzinfo=UTC)','16:55 owned operation deadline':'2026-10-02 00:55 owned operation deadline','schedulerは16:55まで継続':'schedulerは2026-10-02 00:55UTCまで継続','quoridor-4lc.38 / .44 recovery scheduler停止':'quoridor-4lc.38 / .44 / .53 deadline scheduler停止',"'recovery_issue':'quoridor-4lc.44'":"'recovery_issue':'quoridor-4lc.53'"}
 for a,b in replacements.items():assert a in s,a;s=s.replace(a,b)
 s=s.replace('    global LAST_GOOD\n','    global LAST_GOOD\n    for path,expected in EXPECTED[\'input_hashes\'].items():\n        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise safe_state.Unavailable(\'Deadline input hash changed: \'+path)\n')
 s=s.replace("ROOT/'tools/ai-sigma-supervisor-read-guard',ROOT/'tools/ai-sigma-scheduler-monitor-recovery',","ROOT/'tools/ai-sigma-supervisor-read-guard',ROOT/'tools/ai-sigma-scheduler-monitor-recovery',\n                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-RECOVERY',\n                 ROOT/'tools/ai-sigma-scheduler-deadline-update',\n                 ROOT/'docs/reports/ai-sigma-steward-deadline-20261002.md',")
 s=s.replace("'deadline_utc':END.isoformat(),","'expected_input_hashes':EXPECTED['input_hashes'],'deadline_utc':END.isoformat(),")
 compile(s,str(TOOLS/'watch.py'),'exec');(TOOLS/'watch.py').write_text(s);(TOOLS/'safe_state.py').write_bytes((OLD/'safe_state.py').read_bytes())
 write('prepared.json',{'at':now(),'operator':proc(os.getpid()),'new_hashes':{str(p):sha(p) for p in [CFG,CFG.parent/'contract.json',prompt,doc,TOOLS/'watch.py',TOOLS/'safe_state.py']},'end':END,'final':'2026-10-02T00:58:00Z','prompt_change':'deadline text only','old_sources_preserved':True})
def reload():
 validation=wrapper('validate');request=wrapper('reload');until=time.monotonic()+20
 while time.monotonic()<until:
  st=state();events=[json.loads(x) for x in (STATE/'events.jsonl').read_text().splitlines()]
  match=[e for e in events if e['event']=='reloaded' and e['at']>=json.loads((OUT/'prepared.json').read_text())['at']]
  if match and st['config_sha256']==sha(CFG) and st['contract_sha256']==sha(CFG.parent/'contract.json'):break
  time.sleep(.1)
 else:raise RuntimeError('Reload not confirmed')
 write('reload-confirmed.json',{'at':now(),'validation':validation,'request':request,'events':match,'state':st,'state_end_at_available':'end_at' in st,'actual_end_bound_by_hash':validation['end_at']})
def replace():
 before=json.loads((OUT/'before.json').read_text());old=before['monitor'];st=state()
 assert st['binding']==before['state']['binding'] and st['process']==before['state']['process'] and alive(st['process']) and alive(old)
 # No owned turn is discarded. Unknown/pending owner is a no-go for this transition.
 assert st.get('owned') is None and not st.get('recovery_required'),'Owned turn requires separate exact recovery; no transition'
 fd=os.pidfd_open(old['pid'])
 try:
  assert alive(old);signal.pidfd_send_signal(fd,signal.SIGTERM)
 finally:os.close(fd)
 sent=now();until=time.monotonic()+120
 while alive(old) and time.monotonic()<until:time.sleep(.1)
 assert not alive(old),'Old monitor still alive; no duplicate launch'
 st=state();assert st['phase']=='stopped' and st['process'] is None and st.get('owned') is None and not st.get('recovery_required'),st
 assert not alive(before['state']['process'])
 write('old-operation-stopped.json',{'at':now(),'signal_at':sent,'monitor':old,'monitor_observed':proc(old['pid']),'scheduler':before['state']['process'],'scheduler_observed':proc(before['state']['process']['pid']),'state':st,'old_monitor_end':json.loads((OLD_RUN/'monitor-ended.json').read_text()),'old_monitor_stop':json.loads((OLD_RUN/'scheduler-end-stop.json').read_text()),'owned_turn_pending':False})
 epoch=now();receipt=wrapper('start');st=state();assert st['phase']=='running' and alive(st['process'])
 run=OUT/('live-'+str(uuid.uuid4()));run.mkdir()
 hashes={str(p):sha(p) for p in [CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',TOOLS/'watch.py',TOOLS/'safe_state.py']}
 expected={'process':st['process'],'binding':st['binding'],'operation_epoch_utc':epoch,'input_hashes':hashes};(run/'expectations.json').write_text(json.dumps(expected,indent=2)+'\n')
 with (run/'console.log').open('w') as log:
  p=subprocess.Popen([sys.executable,'-B',str(TOOLS/'watch.py'),'--run-dir',str(run),'--expectations',str(run/'expectations.json')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 ident=proc(p.pid);until=time.monotonic()+15
 while time.monotonic()<until:
  if (run/'monitor-observation.json').exists():break
  if p.poll() is not None:raise RuntimeError('New monitor exited; inspect own console')
  time.sleep(.1)
 else:raise RuntimeError('New monitor observation unavailable')
 write('live-transition.json',{'at':now(),'operator':proc(os.getpid()),'start_receipt':receipt,'state':state(),'scheduler_observed':proc(st['process']['pid']),'monitor':ident,'run':str(run),'monitor_process':json.loads((run/'monitor-process.json').read_text()),'monitor_observation':json.loads((run/'monitor-observation.json').read_text()),'old_stop_at':sent,'new_start_epoch':epoch,'expectations':expected,'full_period_success_claimed':False})

def observe():
 before=json.loads((OUT/'before.json').read_text());live=json.loads((OUT/'live-transition.json').read_text());run=Path(live['run']);st=state()
 assert st['binding']==before['state']['binding'] and st['process']==live['state']['process'] and alive(st['process']) and alive(live['monitor'])
 assert not alive(before['monitor']) and not alive(before['state']['process'])
 hashes=live['expectations']['input_hashes'];assert all(sha(p)==h for p,h in hashes.items())
 unchanged=[{**r,'after_sha256':sha(r['path']),'unchanged':sha(r['path'])==r['sha256']} for r in before['immutable_refs']]
 assert all(r['unchanged'] for r in unchanged)
 old_sources=before['edited_or_copy_sources'][4:];assert all(sha(r['path'])==r['sha256'] for r in old_sources)
 processes={}
 for p in OUT.glob('short-*-end.json'):
  v=json.loads(p.read_text());identity=v['process'];processes[(identity['pid'],identity['start_ticks'])]=identity
 for line in (OUT/'commands.jsonl').read_text().splitlines():
  r=json.loads(line);identity=r['identity']
  if identity:processes[(identity['pid'],identity['start_ticks'])]=identity
 checks=[{'expected':r,'current':proc(r['pid']),'same_identity_alive':alive(r)} for r in processes.values()]
 assert not any(r['same_identity_alive'] for r in checks)
 seen=set();allocated=0;logical=0
 for root in [OUT,TOOLS,ROOT/'docs/reports/ai-sigma-steward-deadline-20261002.md']:
  stack=[root]
  while stack:
   p=stack.pop()
   try:s=p.lstat()
   except FileNotFoundError:continue
   k=(s.st_dev,s.st_ino)
   if k in seen:continue
   seen.add(k);allocated+=s.st_blocks*512;logical+=s.st_size
   if p.is_dir() and not p.is_symlink():stack.extend(p.iterdir())
 assert allocated<32*1024**2
 obs=json.loads((run/'monitor-observation.json').read_text());assert obs['own_scope_allocated_peak_bytes']<112*1024**2
 write('after.json',{'at':now(),'state':st,'events':[json.loads(x) for x in (STATE/'events.jsonl').read_text().splitlines() if json.loads(x)['at']>=live['new_start_epoch']],'scheduler_observed':proc(st['process']['pid']),'monitor_observed':proc(live['monitor']['pid']),'input_hashes':hashes,'immutable_refs':unchanged,'old_watch_and_safe_state_unchanged':True,'monitor_observation':obs,'state_end_at_available':'end_at' in st,'actual_end_at_validation':json.loads((OUT/'reload-confirmed.json').read_text())['validation']['end_at'],'new_scope_unique_allocated_bytes':allocated,'new_scope_logical_bytes':logical,'ram_limit_as':resource.getrlimit(resource.RLIMIT_AS),'cpu0':list(os.sched_getaffinity(0)),'no_new_reservation':True,'cumulative_12GiB_not_reset':True,'outer_initial_read_and_verify_launcher_pid_missing':True,'reload_cli_argument_failure_retained':True})
 write('short-jobs-stopped.json',{'at':now(),'known_short_identity_count':len(checks),'known_short_checks':checks,'no_known_short_identity_alive':True,'recorder_process':proc(os.getpid()),'recorder_exits_after_record_and_short_end':'caller checks synchronous exit_code=0','initial_read_and_verify_launcher_pid_missing':True,'long_scheduler':st['process'],'long_monitor':live['monitor'],'long_processes_continue':True,'scheduler_stop_at':'2026-10-02T00:55:00Z','monitor_collect_by':'2026-10-02T00:58:00Z','final_evidence_by':'2026-10-02T01:00:00Z','owner':'codex:01a0f31d-99ee-7d63-b162-bc1a59c457c6','all_research_pid_zero_claimed':False})

if __name__=='__main__':
 try:globals()[sys.argv[1]]()
 finally:
  r=resource.getrusage(resource.RUSAGE_SELF);write('short-'+sys.argv[1]+'-'+str(uuid.uuid4())+'-end.json',{'at':now(),'process':proc(os.getpid()),'self_maxrss_kib':r.ru_maxrss,'exit_record_before_return':True})
