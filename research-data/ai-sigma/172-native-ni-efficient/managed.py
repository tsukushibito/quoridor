import os,pathlib,time,subprocess,json,datetime,sys,hashlib
os.sched_setaffinity(0,{0});D=pathlib.Path(__file__).parent;start=time.monotonic();intake=json.loads((D/'intake.json').read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(intake['newcommand_deadline']);name=sys.argv[1];args=sys.argv[2:];used=20+sum(json.loads(p.read_text())['elapsed_seconds'] for p in D.glob('*.process.json'));assert used<180
with (D/(name+'.log')).open('wb') as out:
 p=subprocess.Popen(args,stdout=out,stderr=subprocess.STDOUT,start_new_session=True);identity=pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[19];peak=0;reason=None
 while p.poll() is None:
  try:peak=max(peak,sum(int(pathlib.Path(q).read_text().rsplit(')',1)[1].split()[21])*os.sysconf('SC_PAGE_SIZE') for q in ['/proc/self/stat',f'/proc/{p.pid}/stat']))
  except FileNotFoundError:pass
  if time.monotonic()-start>min(60,180-used):reason='TIME_GUARD'
  if peak>939524096:reason='RAM_GUARD'
  if reason:p.terminate();break
  time.sleep(.02)
 try:code=p.wait(timeout=3)
 except subprocess.TimeoutExpired:p.kill();code=p.wait(timeout=3)
rec={'run':name,'command':args,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'prior_reserved_seconds':used,'exit':code,'reason':reason,'PID':p.pid,'start_ticks':identity,'current_identity_absent':not pathlib.Path(f'/proc/{p.pid}').exists(),'wait_complete':True,'CPU':[0],'sampled_parent_child_RSS_peak':peak,'guard':939524096,'instant_peak_unknown':True,'source_SHA':hashlib.sha256(pathlib.Path(args[-1]).read_bytes()).hexdigest(),'new_NN':0};(D/(name+'.process.json')).write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));sys.exit(code)
