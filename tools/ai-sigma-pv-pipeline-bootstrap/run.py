"""Bounded own static command runner; never launches research engines."""
import datetime, hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path
D=Path('research-data/ai-sigma/160-pv-pipeline-bootstrap')
command=sys.argv[1]; assert command in ('export','validate','smoke')
assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-03T03:17:00+00:00')
logs=list(D.glob('command-*.json')); elapsed=sum(json.loads(p.read_text()).get('elapsed_seconds',0) for p in logs)
assert elapsed<70  # leave management allowance within static90
run=f'{command}-{len(logs)}'; start=time.time()
cmd=['taskset','-c','0','python3','tools/ai-sigma-pv-pipeline-bootstrap/bootstrap.py',command]
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
identity={'pid':p.pid,'starttick':Path(f'/proc/{p.pid}/stat').read_text().split(') ')[1].split()[19],'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
try: stdout,stderr=p.communicate(timeout=min(60,70-elapsed))
except subprocess.TimeoutExpired:
    p.kill(); stdout,stderr=p.communicate()
result={'run':run,'command':cmd,'start_epoch':start,'end_epoch':time.time(),'elapsed_seconds':time.time()-start,'returncode':p.returncode,'stdout':stdout.decode(),'stderr':stderr.decode(),'identity':identity,'own_wait_completed':p.poll() is not None,'new_NN':0,'source_sha256':hashlib.sha256(Path(cmd[-2]).read_bytes()).hexdigest(),'children_peak_RSS_KiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
(D/f'command-{run}.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result)); sys.exit(p.returncode)
