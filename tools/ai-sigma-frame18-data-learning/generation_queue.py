"""Bounded background production sequence; one fresh admission per immutable chunk."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
R=Path.cwd();T=R/'tools/ai-sigma-frame18-data-learning';D=R/'research-data/ai-sigma/frame18-data-learning'
os.sched_setaffinity(0,{0})
settings=json.loads(Path(sys.argv[1]).read_text());state=D/'background-generation-progress.json'
for p,h in settings['sources'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
start=time.monotonic();idle=0.;managed=0.;finished=[];reason=None
def save():
    state.write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'queue_pid':os.getpid(),
      'finished_chunks':finished,'idle_wait_s':idle,'management_measured_s':managed,'reason':reason,
      'elapsed_s':time.monotonic()-start,'receipt_not_science_success':True},indent=2)+'\n')
def run(cmd,limit):
    global managed
    st=time.monotonic()
    try:subprocess.run(cmd,check=True,timeout=limit)
    finally:managed+=time.monotonic()-st;save()
try:
    for name in settings['chunks']:
        config=D/f'{name}-config.json';c=json.loads(config.read_text());O=Path(c['job_out'])
        assert not (O/'actual-start.json').exists(),'SUCCESS_OR_STARTED_CHUNK_REENTRY_FORBIDDEN'
        while True:
            if time.time()>=datetime.datetime.fromisoformat('2026-10-04T12:50:00+00:00').timestamp():
                reason='NEW_GENERATION_START_CUTOFF';save();raise SystemExit(0)
            if (D/'BACKGROUND_STOP').exists():reason='OWNER_STOP';save();raise SystemExit(0)
            sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
            assert sch['phase']=='running'and not sch.get('recovery_required')
            if sch['owned']is None and sch.get('next_at')and sch['next_at']-time.time()>=330:break
            st=time.monotonic();time.sleep(5);idle+=time.monotonic()-st;save()
        # Exactly one actual guardian invocation; its unknown/fault is retained and wakes the owner.
        subprocess.run(['/usr/bin/python3','-B',str(T/'gen_guard_background.py'),str(config)],check=True,timeout=340)
        proc=json.loads((O/'process.json').read_text());assert proc['all_child_waited']and proc['current_exact_absent']
        run(['taskset','-c','2','/home/vscode/.local/bin/node','--max-old-space-size=512',str(T/'qualify.cjs'),str(config)],60)
        run(['taskset','-c','2','/home/vscode/.local/bin/node','--max-old-space-size=512',str(R/'tools/ai-sigma-teacher-throughput/fresh96-stage/export_generated.cjs'),c['openings_path'],str(O/'effective-rows.jsonl.gz'),str(O/'metadata.jsonl.gz'),str(O/'labels.jsonl.gz')],60)
        run(['taskset','-c','2','/usr/bin/python3','-B',str(T/'pack.py'),str(config)],60)
        # No raw/winner/fullstatus is placed in the public progress interface.
        summary=json.loads((O/'summary.json').read_text())
        finished.append({'chunk':name,'completed':sum(summary['status_counts'].get(k,0)for k in['GOAL','DRAW200','DRAW_NOLEGAL']),
          'planned':48,'Rjoint':summary['Rjoint'],'physicalNN':proc['sample_equivalent'],'wall_s':proc['jobwall_seconds'],
          'current_exact_absent':True,'metadata':str(O/'metadata.jsonl.gz')})
        save();assert managed<450,'MANAGEMENT_RESIDUAL_REQUIRED'
    run(['taskset','-c','2','/usr/bin/python3','-B',str(T/'build_dataset.py')],60)
    run(['taskset','-c','2','/usr/bin/python3','-B',str(T/'learning_plan.py'),'--dataset',str(D/'dataset-v1')],60)
    reason='ALL_GENERATION_CHUNKS_AND_LEARNING_PLAN_FINISHED';save()
except BaseException as exc:
    if reason is None:reason=type(exc).__name__+':'+str(exc);save()
    raise
