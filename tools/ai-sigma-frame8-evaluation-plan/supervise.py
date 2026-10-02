import subprocess,os,json,time,datetime,hashlib,signal,resource,sys
from pathlib import Path
O=Path('.artifacts/ai-sigma/resume-20261002/FRAME8-EVALUATION-PLAN').resolve();O.mkdir(exist_ok=True);tmp=O/'tmp';tmp.mkdir(exist_ok=True);os.sched_setaffinity(0,{0});boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def proc(pid):
 try:
  s=Path(f'/proc/{pid}/stat').read_text().split(') ')[1].split();return {'pid':pid,'ppid':int(s[1]),'starttick':int(s[19]),'currentRSS':int(s[21])*os.sysconf('SC_PAGE_SIZE'),'state':s[0]}
 except FileNotFoundError:return None
name=sys.argv[1] if len(sys.argv)>1 else 'arithmetic-new';assert not (O/(name+'.process.json')).exists(),'RUN_ALREADY_EXISTS'
cmd=['python3','-B','tools/ai-sigma-frame8-evaluation-plan/arithmetic.py'];start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();env=os.environ.copy();env.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),XDG_CACHE_HOME=str(tmp),XDG_CONFIG_HOME=str(tmp))
def child_limits():
 os.sched_setaffinity(0,{0});resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with (O/(name+'.log')).open('wb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,preexec_fn=child_limits);initial=proc(p.pid);peak=0;samples=[];reason=None
 while p.poll() is None:
  own=proc(os.getpid());child=proc(p.pid);rss=own['currentRSS']+(child['currentRSS'] if child else 0);peak=max(peak,rss);samples.append({'mono':time.monotonic(),'RSS':rss})
  if rss>=448*1024*1024 or time.monotonic()-start>=30:
   reason='RSS_GUARD' if rss>=448*1024*1024 else 'TIMEOUT';current=proc(p.pid)
   if current and current['starttick']==initial['starttick']:p.terminate()
   try:p.wait(timeout=1)
   except subprocess.TimeoutExpired:
    current=proc(p.pid)
    if current and current['starttick']==initial['starttick']:p.kill()
   break
  time.sleep(.01)
 code=p.wait()
r={'issue':'quoridor-4lc.116','run':name,'startUTC':utc,'endUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed':time.monotonic()-start,'CPU_number':[0],'logical_count':1,'RAM':512*1024*1024,'currentRSSguard':448*1024*1024,'observed_RSSpeak_parent_child':peak,'initial':initial,'boot':boot,'command':cmd,'commandSHA':hashlib.sha256(json.dumps(cmd).encode()).hexdigest(),'sourceSHA':hashlib.sha256(Path(cmd[-1]).read_bytes()).hexdigest(),'exit':code,'reason':reason,'waited':True,'current_same_identity':proc(p.pid),'sample_count':len(samples),'instantpeak_shortcommand_TID_not_guaranteed':True,'NN_GPU_Chrome_build_game':0};(O/(name+'.process.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));assert code==0 and reason is None
