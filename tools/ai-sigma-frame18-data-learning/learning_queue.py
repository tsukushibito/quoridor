"""Two prespecified stage jobs, background waiting for fresh natural physical windows."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
R=Path.cwd();T=R/'tools/ai-sigma-frame18-data-learning';D=R/'research-data/ai-sigma/frame18-data-learning'
os.sched_setaffinity(0,{0});settings=json.loads(Path(sys.argv[1]).read_text());started=time.monotonic();idle=0.;done=[]
for p,h in settings['sources'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
def save(reason=None):
 (D/'background-learning-progress.json').write_text(json.dumps(dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),finished=done,idle_wait_s=idle,elapsed_s=time.monotonic()-started,reason=reason),indent=2)+'\n')
for planned in[192,576]:
 p=D/'learning-plan-v1'/f'settings-{planned}.json'
 while True:
  assert time.time()<datetime.datetime.fromisoformat('2026-10-04T13:40:00+00:00').timestamp(),'LEARNING_START_CUTOFF'
  sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
  assert sch['phase']=='running'and not sch.get('recovery_required')
  if sch['owned']is None and sch['next_at']-time.time()>=330:break
  st=time.monotonic();time.sleep(5);idle+=time.monotonic()-st;save()
 subprocess.run(['/usr/bin/python3','-B',str(T/'learn_guard.py'),str(p)],check=True,timeout=340)
 c=json.loads(p.read_text());proc=json.loads((Path(c['guardian_out'])/'process.json').read_text());assert proc['all_child_waited']and proc['current_exact_absent']
 summary=json.loads((Path(c['output'])/c['run_id']/'summary.json').read_text())
 done.append(dict(stage=planned,G=c['positive_train_G'],samples=proc['samples_actual'],wall_s=proc['wall_s'],best_step=summary['best_step'],best_val_gameMSE=summary['best_validation_mse']))
 save()
save('TWO_STAGES_STOPPED')
