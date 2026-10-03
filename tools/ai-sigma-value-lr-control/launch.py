"""188 r2 finite CPU8 manager; preflight/admission precede one science child."""
import datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path
D=Path('research-data/ai-sigma/188-value-lr-control/runs/r2')
def utc():return datetime.datetime.now(datetime.timezone.utc)
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def proc(pid):
 p=Path('/proc')/str(pid);st=(p/'stat').read_text().rsplit(')',1)[1].split()
 return dict(pid=int(pid),tick=st[19],RSS=int(st[21])*os.sysconf('SC_PAGE_SIZE'),ppid=int(st[1]),pgrp=int(st[2]))
assert os.sched_getaffinity(0)=={8}
pr=json.loads((D/'preregister.json').read_text());deadline=datetime.datetime.fromisoformat(pr['newscience_before_UTC'].replace('Z','+00:00'))
assert utc()<deadline,'NEW_SCIENCE_DEADLINE'
script=Path('tools/ai-sigma-value-lr-control/learn.py');assert hashlib.sha256(script.read_bytes()).hexdigest()==pr['learn_source_SHA256']
command=['/home/vscode/.cache/inference/envs/quoridor-training/bin/python','-B',str(script)];assert os.access(command[0],os.X_OK)
owner=json.loads((D/'owner-receipt.json').read_text());assert owner['self']['status']=='in_progress' and owner['self']['assignee']=='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418'
assert all('paused-by-user' not in x.get('labels',[]) for x in owner.values())
own={os.getpid()};cur=os.getpid()
while cur>1:cur=proc(cur)['ppid'];own.add(cur)
active=[];services=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)in own:continue
 try:
  cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  if ('ai-sigma'in cmd or'research-team'in cmd)and any(s in cmd for s in ['python','node','faithful-native']):
   r=proc(p.name);r['cmd']=cmd[:500]
   (services if 'scheduler.py run'in cmd or'/watch.py 'in cmd else active).append(r)
 except (FileNotFoundError,ProcessLookupError):pass
stage=json.loads(Path('research-data/ai-sigma/187-manygame-generation/intake.json').read_text())
scheduler=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
forecast=1073741824+1073741824+536870912+sum(x['RSS']for x in active+services)
save('admission.json',dict(UTC=utc().isoformat(),active=active,services=services,stage187=stage,scheduler_owned=scheduler.get('owned'),next_observe=scheduler.get('next_at'),RSS_forecast=forecast,CPU=[8],child_CPU_count=1,unknown_active_rejected=True))
assert not active,'CURRENT_ACTIVE_JOB_OR_UNKNOWN_OWNER'
assert stage['scientific_started'] is False,'187_SCIENCE_OVERLAP'
assert forecast<=8589934592,'AGGREGATE_RAM_GUARD'
assert utc()<deadline,'NEW_SCIENCE_DEADLINE'
assert not(D/'process-stop.json').exists(),'NO_SUCCESS_REPLACEMENT'
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','UV_NO_SYNC':'1','UV_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
started=time.monotonic();peak=0;reason=None;tracked={};startedUTC=utc().isoformat()
with(D/'stdout.txt').open('w')as out,(D/'stderr.txt').open('w')as err:
 child=subprocess.Popen(command,env=env,stdout=out,stderr=err,start_new_session=True)
 identity=proc(child.pid);save('owned-current.json',dict(identity=identity,command=command,started_UTC=startedUTC))
 while child.poll()is None:
  family=[]
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    r=proc(p.name)
    if r['pgrp']==child.pid:family.append(r);tracked[(r['pid'],r['tick'])]=r
   except(FileNotFoundError,ProcessLookupError):pass
  peak=max(peak,sum(r['RSS']for r in family))
  if peak>939524096:reason='FAMILY_RSS_GUARD'
  if time.monotonic()-started>30:reason='TIME_GUARD'
  if utc()>=datetime.datetime.fromisoformat(pr['science_before_UTC'].replace('Z','+00:00')):reason='SCIENCE_DEADLINE'
  if reason:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=1)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
   break
  time.sleep(.02)
 code=child.wait()
remaining=[]
for r in tracked.values():
 try:
  if proc(r['pid'])['tick']==r['tick']:remaining.append(r)
 except(FileNotFoundError,ProcessLookupError):pass
save('process-stop.json',dict(identity=identity,tracked=list(tracked.values()),command=command,exit=code,reason=reason,wall_seconds=time.monotonic()-started,peak_family_RSS_bytes=peak,waited=True,current_identity_absent=not remaining,remaining=remaining,CPU_affinity=[8],started_UTC=startedUTC,stopped_UTC=utc().isoformat(),GPU_calls=0))
assert not remaining,'OWNED_CHILD_NOT_REAPED'
print(json.dumps(dict(exit=code,reason=reason,wall_seconds=time.monotonic()-started,peak_family_RSS_bytes=peak)))
