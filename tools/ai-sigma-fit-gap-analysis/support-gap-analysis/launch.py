"""One bounded CPU2 control, adapting immutable guardian only in memory."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,os,time,types
R=Path.cwd();D=R/'research-data/ai-sigma/frame16-fit-gap-analysis/support-gap-analysis';T=R/'tools/ai-sigma-fit-gap-analysis';P=R/'tools/nnue-training/manage_frame14.py';h=hashlib.sha256(P.read_bytes()).hexdigest();assert h=='cf13f3e0e1cf5d2784cad19b64d7cb1917d099785cb7f515b40a3abd927c2286'
s=P.read_text().replace("state('quoridor-4lc.195')","state('quoridor-4lc.216')").replace('codex:01a0f31c-2e4b-7170-82c5-69e1428c2418','codex:01a0f31d-6d15-7620-bb63-4b4f878e4746').replace('900 if a.kind', '180 if a.kind').replace('else 1200','else 180').replace('spent+a.seconds>', 'spent+144.412996+a.seconds>').replace('charged+a.samples>5000000','charged+a.samples>30000')
m=types.ModuleType('private211guardian');m.__file__=str(P);exec(compile(s,str(P)+' [211 owner adaptation]','exec'),m.__dict__);m.D=D;m.GUARD=448*1024**2
p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--kind',default='static');p.add_argument('--seconds',type=float,default=60);p.add_argument('--samples',type=int,default=0);p.add_argument('--result');p.add_argument('--new',default='2026-10-04T07:25:00Z');p.add_argument('--stop',default='2026-10-04T07:30:00Z');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();a.command=a.command[1:]if a.command and a.command[0]=='--'else a.command
assert a.command and a.kind=='static' and 0<a.seconds<=15 and a.samples<=30000
sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert sch['phase']=='running' and sch['owned'] is None and sch['next_at']-time.time()>a.seconds+30,'SUPERVISOR_CURRENT_OR_SHORT_WINDOW'
for row in m.current():
 if row['pid']==os.getpid() or row['cmd'].startswith('/bin/bash -c '):continue
 script=next((x for x in row['cmd'].split()if x.endswith(('.py','.cjs'))),'')
 if str(T)in row['cmd']:continue
 if ('tools/ai-sigma-'in script or 'tools/nnue-training/'in script or ('research-data/ai-sigma/'in script and script.endswith(('check.py','check_fourth.py'))))and not script.endswith(('/save.py','/save_git.py','/plot.py','/plot_curves.py')):
  raise ValueError('current other science/critic/helper '+str((row['pid'],row['tick'],script)))
st=json.loads((D/'storage-admission.json').read_text());assert st['forecast_B']<st['guard_B']==15*1024**2 and st['reservation_B']==16*1024**2 and st['transfer_confirmed']
reg=json.loads((D/'preregister.json').read_text())
for path,h in reg['bindings'].items():assert hashlib.sha256((R/path).read_bytes()).hexdigest()==h,path
prior_CV=sum(json.loads(p.read_text())['wall_seconds'] for p in (D/'jobs').glob('*/process.json'));assert prior_CV+a.seconds<=15,'PHASE5_MATH_CAP15';m.main(a)
