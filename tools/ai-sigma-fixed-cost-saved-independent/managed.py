import datetime,json,os,pathlib,signal,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/FIXED-COST-SAVED-INDEPENDENT'
run=sys.argv[1];cmd=sys.argv[2:];os.sched_setaffinity(0,{0})
assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-02T18:30:18.578017+00:00')
env=dict(os.environ,UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(O/'tmp'),XDG_CACHE_HOME=str(O/'xdg'))
for n in ['tmp','xdg']:(O/n).mkdir(exist_ok=True)
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();peak=0;owned={};reason=None
with (O/(run+'.log')).open('w') as log:
 p=subprocess.Popen(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 def scan():
  rss=0;current=[]
  for q in pathlib.Path('/proc').iterdir():
   if not q.name.isdigit():continue
   try:
    s=(q/'stat').read_text().rsplit(')',1)[1].split()
    if int(s[2])!=p.pid and int(q.name)!=os.getpid():continue
    ident=(int(q.name),int(s[19]));owned[ident]={'pid':ident[0],'start_ticks':ident[1],'pgrp':int(s[2])};current.append(ident);rss+=int(s[21])*os.sysconf('SC_PAGE_SIZE')
   except FileNotFoundError:pass
  return rss,current
 while p.poll() is None:
  rss,_=scan();peak=max(peak,rss)
  if rss>448*1024**2 or time.monotonic()-start>60:
   reason='RSSguard' if rss>448*1024**2 else 'timeout';os.killpg(p.pid,signal.SIGTERM);break
  time.sleep(.01)
 try:code=p.wait(timeout=2)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
 _,current=scan();remaining=[owned[k] for k in current if k[0]!=os.getpid()]
 result={'run':run,'command':cmd,'UTC_start':utc,'UTC_end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_s':time.monotonic()-start,'exit':code,'reason':reason,'peak_observed_RSS':peak,'CPU':[0],'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'owned':list(owned.values()),'remaining':remaining,'unknown_not_signalled':True,'short_child_between_samples_missing':True}
 (O/(run+'.process.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(code)
