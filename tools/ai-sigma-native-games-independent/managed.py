import os,pathlib,sys,json,time,subprocess,datetime,resource,hashlib
os.sched_setaffinity(0,{0});ROOT=pathlib.Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/169-native-games-independent';name=sys.argv[1];args=sys.argv[2:];assert name in ['replay-r1','replay-r2','binding-r1','aux-r1','finalize-r1']
intake=json.loads((D/'intake.json').read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(intake['newcommand_deadline'])
# R1's exact elapsed is unavailable; reserve its whole60s cap plus20s earlier management.
used=20+sum(json.loads(p.read_text())['elapsed_seconds'] for p in D.glob('*.process.json'));assert used<180
start=time.monotonic();peak=0
with (D/(name+'.log')).open('wb') as f:
 p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 identity=(pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split())[19]
 reason=None
 while p.poll() is None:
  elapsed=time.monotonic()-start
  try:childrss=int(pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[21])*os.sysconf('SC_PAGE_SIZE');parentrss=int(pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[21])*os.sysconf('SC_PAGE_SIZE');peak=max(peak,childrss+parentrss)
  except FileNotFoundError:pass
  if peak>=939524096:reason='RSS_GUARD'
  elif elapsed>=min(60,180-used):reason='TIME_GUARD'
  if reason:p.terminate();break
  time.sleep(.02)
 try:code=p.wait(timeout=3)
 except subprocess.TimeoutExpired:p.kill();code=p.wait(timeout=3)
 elapsed=time.monotonic()-start
result={'run':name,'command':args,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashlib.sha256(pathlib.Path(args[-1]).read_bytes()).hexdigest(),'exit':code,'reason':reason,'elapsed_seconds':elapsed,'prior_conservative_seconds':used,'total_conservative_seconds':used+elapsed,'RAM_family_sampled_peak':peak,'RAM_guard':939524096,'CPU':[0],'PID':p.pid,'start_ticks':identity,'wait_completed':True,'current_identity_absent':not pathlib.Path(f'/proc/{p.pid}').exists(),'new_NN':0,'owned_CHILD':1,'instant_RSS_peak_unknown':True}
(D/(name+'.process.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(code)
