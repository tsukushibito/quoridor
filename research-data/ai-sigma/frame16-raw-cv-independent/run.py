import os,pathlib,json,subprocess,time,hashlib,datetime,resource
os.sched_setaffinity(0,{0});D=pathlib.Path('research-data/ai-sigma/frame16-raw-cv-independent'); start=time.monotonic(); prior=json.load(open(D/'process-attempt2.json'))['all_attempt_wall']
s=json.load(open('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json'));assert s['owned'] is None and s['next_at']-time.time()>150
stop=json.load(open('research-data/ai-sigma/frame16-fit-gap-analysis/raw-cv-control/science-source-stop-receipt.json'));assert stop['scientific_source_writing_stopped'] is True
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
checks={}
for k in ('source_SHA','immutable_input_SHA','immutable_result_SHA'):
 for p,h in stop[k].items():assert sha(p)==h,p;checks[p]=h
assert not pathlib.Path('/proc/4102202').exists() or pathlib.Path('/proc/4102202/stat').read_text().split()[21]!='35003273'
current=[]
for q in pathlib.Path('/proc').iterdir():
 if not q.name.isdigit() or q.name==str(os.getpid()):continue
 try:
  cmd=(q/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');stat=(q/'stat').read_text().split()
  if ('python' in cmd or 'node' in cmd) and any(v in cmd for v in ('tools/ai-sigma','tools/nnue','guardian.py','save_git.py')) and 'python3 -B -'not in cmd and 'frame16-raw-cv-independent/run.py'not in cmd:current.append(dict(pid=int(q.name),tick=stat[21],RSS=int(stat[23])*4096,cmd=cmd[:250]))
 except (OSError,ValueError):pass
assert not current,current
scope=sum(p.stat().st_size for p in D.iterdir()if p.is_file());forecast=scope+160000+262144+65536+131072;assert forecast<716800 and 115978724+1048576<117440512
pidstat=pathlib.Path('/proc/self/stat').read_text().split();admit=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),owned=None,quiet_seconds=s['next_at']-time.time(),owner_source_stop='science-source-stop-receipt.json',source_receipt_SHA=sha('research-data/ai-sigma/frame16-fit-gap-analysis/raw-cv-control/science-source-stop-receipt.json'),ownPID=os.getpid(),tick=pidstat[21],RSS=int(pidstat[23])*4096,current_matching_scientific=[],scope=scope,forecast=forecast,scope_guard=716800,old_undiscounted=115978724,reserve=1048576,total=117027300,critic_guard=117440512,bindings=checks,point_only=True)
(D/'admission.json').write_text(json.dumps(admit,indent=2)+'\n')
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1');command=['/home/vscode/.cache/inference/envs/quoridor-training/bin/python','-B',str(D/'check.py')]
p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env);tick=pathlib.Path('/proc/%s/stat'%p.pid).read_text().split()[21]
try:out,err=p.communicate(timeout=max(1,59-prior-(time.monotonic()-start)))
except subprocess.TimeoutExpired:p.kill();out,err=p.communicate()
(D/'calc.stdout').write_bytes(out);(D/'calc.stderr').write_bytes(err)
assert all(sha(v)==h for v,h in checks.items()),'immutable changed'
receipt=dict(command=command,PID=p.pid,tick=tick,exit=p.returncode,wait=True,current_exact_absent=not pathlib.Path('/proc/%s'%p.pid).exists(),wall=time.monotonic()-start,all_attempt_wall=prior+time.monotonic()-start,static_charge=120,cap=120,source_read_charge=60,calc_charge=60,NN=0,CPU=[0],threads=1,failed_checker_not_scientific_negative=p.returncode!=0)
(D/'process.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print(out.decode()[:700]);print(err.decode()[:1000])
