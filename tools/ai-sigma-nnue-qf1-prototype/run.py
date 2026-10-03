"""190 finite CPU8 manager; preflight/admission precede one science child."""
import datetime,hashlib,json,os,signal,subprocess,time,sys
from pathlib import Path
D=Path('research-data/ai-sigma/190-nnue-qf1-prototype')
def utc():return datetime.datetime.now(datetime.timezone.utc)
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def proc(pid):
 p=Path('/proc')/str(pid);st=(p/'stat').read_text().rsplit(')',1)[1].split()
 return dict(pid=int(pid),tick=st[19],RSS=int(st[21])*os.sysconf('SC_PAGE_SIZE'),ppid=int(st[1]),pgrp=int(st[2]))
assert os.sched_getaffinity(0)=={8}
pr=json.loads((D/'preregister.json').read_text());deadline=datetime.datetime.fromisoformat(pr['newscience'].replace('Z','+00:00'))
assert utc()<deadline,'NEW_SCIENCE_DEADLINE'
phase=sys.argv[1];assert phase in ['mock','learn','native']
script=Path('tools/ai-sigma-nnue-qf1-prototype/'+{'mock':'prepare.cjs','learn':'learn.py','native':'probe.cjs'}[phase]);assert hashlib.sha256(script.read_bytes()).hexdigest()==pr['sources'][str(script)]
command=['/home/vscode/.cache/inference/envs/quoridor-training/bin/python','-B',str(script)] if phase=='learn' else ['/home/vscode/.local/bin/node',str(script)]
assert os.access(command[0],os.X_OK)
previous=sum(json.loads(p.read_text())['wall_seconds'] for p in D.glob('process-*.json'))
assert previous<60,'TOTAL_SCIENCE_TIME'
D=D/phase;D.mkdir(exist_ok=True)
owner=json.loads((D.parent/'owner-receipt.json').read_text());assert owner['self']['status']=='in_progress' and owner['self']['assignee']=='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418'
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
stage=json.loads(Path('research-data/ai-sigma/187-manygame-generation/science-stop.json').read_text())
scheduler=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
forecast=1073741824+1073741824+536870912+sum(x['RSS']for x in active+services)
save('admission.json',dict(UTC=utc().isoformat(),active=active,services=services,stage187=stage,scheduler_owned=scheduler.get('owned'),next_observe=scheduler.get('next_at'),RSS_forecast=forecast,CPU=[8],child_CPU_count=1,unknown_active_rejected=True))
assert not active,'CURRENT_ACTIVE_JOB_OR_UNKNOWN_OWNER'
assert stage['science_stopped'] and stage['all_owned_science_children_waited'] and not stage['current_same_identity'],'187_SCIENCE_OVERLAP'
assert forecast<=8589934592,'AGGREGATE_RAM_GUARD'
assert utc()<deadline,'NEW_SCIENCE_DEADLINE'
assert not(D.parent/('process-'+phase+'.json')).exists(),'NO_SUCCESS_REPLACEMENT'
env={**os.environ,'CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','UV_NO_SYNC':'1','UV_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
started=time.monotonic();peak=0;reason=None;tracked={};startedUTC=utc().isoformat()
out=None
with(D/'stderr.txt').open('w')as err:
 child=subprocess.Popen(command,env=env,stdout=subprocess.DEVNULL if phase=='mock' else (D/'stdout.txt').open('w'),stderr=err,start_new_session=True)
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
  if time.monotonic()-started>30 or previous+time.monotonic()-started>60:reason='TIME_GUARD'
  if utc()>=datetime.datetime.fromisoformat(pr['science_stop'].replace('Z','+00:00')):reason='SCIENCE_DEADLINE'
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
D=D.parent
save('process-'+phase+'.json',dict(identity=identity,tracked=list(tracked.values()),command=command,exit=code,reason=reason,wall_seconds=time.monotonic()-started,peak_family_RSS_bytes=peak,waited=True,current_identity_absent=not remaining,remaining=remaining,CPU_affinity=[8],started_UTC=startedUTC,stopped_UTC=utc().isoformat(),GPU_calls=0))
assert not remaining,'OWNED_CHILD_NOT_REAPED'
print(json.dumps(dict(exit=code,reason=reason,wall_seconds=time.monotonic()-started,peak_family_RSS_bytes=peak)))
