import datetime, hashlib, json, os, pathlib, signal, subprocess, sys, time
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/150-sigma-web-port-conformance'
os.sched_setaffinity(0,{0}); run=sys.argv[1]; cmd=sys.argv[2:]
intake=json.loads((D/'intake.json').read_text()); deadline=datetime.datetime.fromisoformat(intake['newcommand_deadline'].replace('Z','+00:00'))
assert datetime.datetime.now(datetime.timezone.utc)<deadline
used=sum(json.loads(p.read_text())['wall_s'] for p in D.glob('*.process.json'));assert used<180
sources={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.glob('*.py')}
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();owned={};peak=0;reason=None
with (D/(run+'.log')).open('w') as log:
 p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 def scan():
  rss=0;alive=[]
  for q in pathlib.Path('/proc').iterdir():
   if not q.name.isdigit():continue
   try:
    a=(q/'stat').read_text().rsplit(')',1)[1].split()
    if int(a[2])!=p.pid and int(q.name)!=os.getpid():continue
    k=(int(q.name),int(a[19]));owned[k]=dict(pid=k[0],starttick=k[1]);alive.append(k);rss+=int(a[21])*os.sysconf('SC_PAGE_SIZE')
   except FileNotFoundError:pass
  return rss,alive
 while p.poll() is None:
  rss,_=scan();peak=max(peak,rss)
  if rss>448*1024**2 or time.monotonic()-start>min(60,180-used) or datetime.datetime.now(datetime.timezone.utc)>=deadline:
   reason='resource_or_deadline';os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(.01)
 try:code=p.wait(timeout=2)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
 _,alive=scan()
result=dict(run=run,command=cmd,UTC_start=utc,UTC_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_s=time.monotonic()-start,exit=code,reason=reason,peak_observed_current_RSS=peak,CPU=[0],RAMguard_bytes=448*1024**2,boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),owned=list(owned.values()),remaining=[owned[k] for k in alive if k[0]!=os.getpid()],source_before=sources,source_after={k:hashlib.sha256((R/k).read_bytes()).hexdigest() for k in sources},child_waited=True,instant_peak_and_short_children_unknown=True,NN_Chrome_game=0)
(D/(run+'.process.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(code)
