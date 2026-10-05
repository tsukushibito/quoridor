import os,subprocess,signal,json,time,sys,datetime
from pathlib import Path
TOOL=Path(__file__).resolve().parent;OUT=TOOL.parents[1]/'.artifacts/ai-sigma/continuation-20261001/SIGMA-KERNEL-OWNERSHIP'
name=sys.argv[1] if len(sys.argv)>1 else 'dummy-kernel-repair-one';os.sched_setaffinity(0,{2});external=subprocess.Popen(['python3','-c','import time;time.sleep(20)']);env=dict(os.environ,SIGMA_EXTERNAL_DUMMY_PID=str(external.pid));start=time.time()
try:
 p=subprocess.Popen(['python3',str(TOOL/'runner.py'),name,'node',str(TOOL/'kernel-dummy.cjs')],env=env);code=p.wait(timeout=15);assert code==0
 assert external.poll() is None
 stat=Path(f'/proc/{external.pid}/stat').read_text().rsplit(')',1)[1].split();assert int(stat[1])==os.getpid()
 (OUT/(name+'-external-owner-proof.json')).write_text(json.dumps({'driver_pid':os.getpid(),'driver_ppid':os.getppid(),'external_PID':external.pid,'external_starttick':int(stat[19]),'PPID_before_stop':int(stat[1]),'kernel_launcher_did_not_spawn_external':True,'external_live_after_tested_cleanup':True,'launcher_exit':code,'duration':time.time()-start,'dedicated_external_owner_signal':'TERM','dedicated_external_owner_wait':True},indent=2)+'\n')
finally:
 external.terminate();exit_code=external.wait(timeout=2);(OUT/(name+'-external-owner-stopped.json')).write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':external.pid,'exit_code':exit_code,'wait_returned':True,'externally_managed':True,'tested_launcher_signal_wait':0},indent=2)+'\n')
