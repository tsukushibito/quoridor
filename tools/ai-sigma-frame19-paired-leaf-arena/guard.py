"""Owned single-CPU learning/test process and cumulative sample guardian."""
from pathlib import Path
import argparse,ctypes,datetime,hashlib,json,os,signal,subprocess,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame19-paired-leaf-arena';T=R/'tools/ai-sigma-frame19-paired-leaf-arena'
p=argparse.ArgumentParser();p.add_argument('settings');a=p.parse_args();c=json.loads(Path(a.settings).read_text());O=Path(c['guardian_out'])
assert O.is_relative_to(D)and not O.exists();O.mkdir(parents=True)
os.sched_setaffinity(0,{2});ctypes.CDLL(None).prctl(36,1,0,0,0)
utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
end=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
save=lambda n,x:(O/n).write_text(json.dumps(x,indent=2)+'\n')
def table():
 tab={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   z=(p/'stat').read_text().rsplit(')',1)[1].split();tab[int(p.name)]=dict(pid=int(p.name),ppid=int(z[1]),tick=int(z[19]),state=z[0],RSS=int(z[21])*4096)
  except(OSError,ValueError):pass
 return tab
tab=table();anc={};pp=tab[os.getpid()]['ppid']
while pp in tab and pp not in anc:anc[pp]=tab[pp]['tick'];pp=tab[pp]['ppid']
def foreign(tab,owned={}):
 found=[]
 for pid,z in tab.items():
  if pid==os.getpid()or z['state']=='Z'or anc.get(pid)==z['tick']or owned.get(pid)==z['tick']:continue
  parent=z['ppid'];seen=set();own=False
  while parent in tab and parent not in seen:
   if parent==os.getpid()or owned.get(parent)==tab[parent]['tick']:own=True;break
   seen.add(parent);parent=tab[parent]['ppid']
  if own:continue
  try:argv=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
  except(OSError,UnicodeError):continue
  executable=Path(argv[0]).name if argv else '';is_interpreter=executable.startswith(('python','node'));script=next((s for s in argv[1:5]if is_interpreter and s.endswith(('.py','.js','.cjs'))and' 'not in s and Path(s).is_file()),'')
  if any(s in script for s in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/'])or (argv and'faithful-native'in argv[0]):found.append(dict(z,script=script,argv=argv[:6]))
 return found
assert time.time()<end(c['newscience_deadline'])
for issue in ['quoridor-4lc','quoridor-4lc.242']:
 q=json.loads(subprocess.check_output(['bash','scripts/dev/beads.sh','show',issue,'--json'],text=True,timeout=10))[0]
 assert q['status']=='in_progress'and'paused-by-user'not in q.get('labels',[])
 if issue.endswith('.242'):assert q['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746'
for p,h in c['sources'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert sch['phase']=='running'and not sch.get('recovery_required')
quiet=sch['next_at']-time.time();assert quiet>=c['hard_s']+30,dict(reason='INSUFFICIENT_PROSPECTIVE_QUIET',quiet=quiet)
loaded=json.loads(Path(c['runtime_loaded']).read_text());assert loaded['frame_start_fixed']=='2026-10-04T22:52:46Z';mon=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mon.stat().st_mtime<120
assert loaded['parent_sha']==hashlib.sha256((R/'docs/design/ai-sigma-continuation-20261001.md').read_bytes()).hexdigest()
for role in ['scheduler','monitor']:
 z=loaded[role].get('process',loaded[role]);assert str(tab[z['pid']]['tick'])==str(z['start_ticks'])
assert not foreign(table()),foreign(table())
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],text=True,timeout=5).strip();assert not gpu
prior=[]
for p in(D/'guardians').glob('*/process.json'):
 z=json.loads(p.read_text());supp=p.with_name('charge-supplement.json')
 if supp.exists():z['samples_charge']=json.loads(supp.read_text())['samples_charge']
 prior.append(z)
assert sum(p['samples_charge']for p in prior)+c['sample_upper']<=2000000
assert sum(p['wall_s']for p in prior)+c['hard_s']<=600
usage=lambda:sum(p.stat().st_size for r in[D,T]for p in r.rglob('*')if p.is_file())
assert usage()+2*1024**2<14*1024**2
assert int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024>2*1024**3
parentRSS=sum(tab[p]['RSS']for p in anc);assert parentRSS+2*1024**3<8*1024**3
save('admission.json',dict(UTC=utc(),scheduler=sch,quiet_s=quiet,current_foreign=[],GPU=[],LLM_owned_not_population_gate=sch.get('owned'),owned_control_ancestor_PIDticks=anc,parent_RSS=parentRSS,storage_current_B=usage(),CPU=[2],torch_threads=1,RAM_guard=1.75*1024**3,allhost_guarantee=False))
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',UV_NO_SYNC='1',UV_OFFLINE='1')
cmd=c['command']
st=time.monotonic();start=utc();tracked={};reason=None;peak=0
with(O/'stdout.txt').open('w')as log:
 child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);tracked[child.pid]=table()[child.pid]['tick']
 def group():
  tab=table();members={p for p,t in tracked.items()if tab.get(p,{}).get('tick')==t};members|={p for p,z in tab.items()if z['ppid']==os.getpid()}
  while True:
   new={p for p,z in tab.items()if z['ppid']in members}
   if new<=members:break
   members|=new
  for p in members:
   if p in tab:tracked[p]=tab[p]['tick']
  return[tab[p]for p in members if p in tab]
 def kill(sig):
  for z in group():
   if z['state']!='Z':
    try:os.kill(z['pid'],sig)
    except ProcessLookupError:pass
 save('actual-start.json',dict(UTC=start,command=cmd,runner_pid=os.getpid(),runner_tick=table()[os.getpid()]['tick']))
 while child.poll()is None:
  members=group();peak=max(peak,sum(z['RSS']for z in members)+table()[os.getpid()]['RSS'])
  if peak>=1.75*1024**3:reason='RAM_GUARD'
  offenders=foreign(table(),tracked)
  if offenders:save('foreign-compute.json',dict(UTC=utc(),offenders=offenders));reason='FOREIGN_COMPUTE_STARTED'
  if time.monotonic()-st>=c['hard_s']or time.time()>=end(c['stop_deadline']):reason='TIME_GUARD'
  if(O/'PAUSE').exists():reason='PAUSED'
  if usage()+2*1024**2>=14*1024**2:reason='STORAGE_GUARD'
  if reason:kill(signal.SIGTERM);break
  time.sleep(.1)
 try:code=child.wait(timeout=2)
 except subprocess.TimeoutExpired:kill(signal.SIGKILL);code=child.wait(timeout=2)
 kill(signal.SIGKILL)
 for _ in range(200):
  try:
   pid,_=os.waitpid(-1,os.WNOHANG)
   if pid==0:time.sleep(.005)
  except ChildProcessError:break
remaining=group();counter=Path(c['counter_file']);data=json.loads(counter.read_text())if counter.exists()else{}
samples=data.get('all_samples',data.get('samples'));receipt=dict(UTC=utc(),startUTC=start,endUTC=utc(),exit=code,reason=reason,wall_s=time.monotonic()-st,peak_family_RSS=peak,
 samples_actual=samples,samples_charge=(min(c['sample_upper'],samples+32768) if samples is not None and (code!=0 or reason) else samples) if samples is not None else c['sample_upper'],original_unknown=samples is None,inflight_NN_unknown=bool(code!=0 or reason),conservative_inflight_upper=32768 if samples is not None and(code!=0 or reason)else 0,
 tracked=tracked,remaining=remaining,all_child_waited=not remaining,current_exact_absent=not remaining,runner_pid=os.getpid(),runner_tick=table()[os.getpid()]['tick'])
save('process.json',receipt);print(json.dumps(receipt));raise SystemExit(0 if code==0 and not reason and not remaining else 1)
