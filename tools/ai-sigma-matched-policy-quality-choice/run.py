import subprocess,time,json,pathlib,datetime,os,signal,hashlib
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/145-matched-policy-quality-choice';O=R/'.artifacts/ai-sigma/resume-20261002/MATCHED-POLICY-QUALITY-CHOICE';intake=json.loads((D/'intake.json').read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(intake['newcommand_deadline']);os.sched_setaffinity(0,{0});cmd=['python3',str(pathlib.Path(__file__).with_name('check.py'))];start=datetime.datetime.now(datetime.timezone.utc).isoformat();mono=time.monotonic();sources={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.iterdir() if p.is_file()}
with (O/'check-r1.log').open('wb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT);tick=int(pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[19]);peak=0;reason=None
 while p.poll() is None:
  try:
   rss=int(pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[21])*4096+int(pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[21])*4096;peak=max(peak,rss)
   if os.sched_getaffinity(p.pid)!={0}:reason='affinity'
  except FileNotFoundError:pass
  if time.monotonic()-mono>55:reason='timeout'
  if peak>=469762048:reason='RSSguard'
  if reason:p.terminate();break
  time.sleep(.02)
 try:code=p.wait(timeout=2)
 except subprocess.TimeoutExpired:p.kill();code=p.wait(timeout=2)
end=datetime.datetime.now(datetime.timezone.utc).isoformat();r={'run':'static-r1','command':cmd,'command_sha256':hashlib.sha256(json.dumps(cmd).encode()).hexdigest(),'start':start,'end':end,'wall_s':time.monotonic()-mono,'child_pid':p.pid,'child_starttick':tick,'exit':code,'stop_reason':reason,'sampled_group_current_RSS_peak':peak,'sample_period_ms':20,'instant_peak_unknown':True,'sources_before':sources,'sources_after':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.iterdir() if p.is_file()},'owned_child_waited':True,'remaining_unknown':0,'other_owner_signal':0,'newNN':0};assert r['sources_before']==r['sources_after'];(D/'run-record.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(code)
