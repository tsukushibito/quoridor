"""Sequential pre-registered jobs. No score-based selection and no blind failure retry."""
import os,json,sys,subprocess,time,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[2];os.chdir(root);os.sched_setaffinity(0,{0});out=root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP';tool=root/'tools/ai-sigma-baseline-gap-frame10';env={**os.environ,'UV_NO_SYNC':'1','UV_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'};pid=os.getpid();tick=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]);log=out/'remaining-controller.jsonl'
def event(kind,**d):
 with log.open('a') as f:f.write(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':kind,'controller_pid':pid,'controller_starttick':tick,**d})+'\n')
event('start',registered_groups=list(range(3,17)),CPU=[0],LLM_and_model_setting_changes=False)
for number in range(3,17):
 run=f'gap149-group{number:02d}-r1';config=out/'configs'/(run+'.json');c=json.loads(config.read_text())
 if time.time()>=datetime.datetime.fromisoformat(c['newjob_deadline']).timestamp():event('stop',reason='NEW_HEAVY_DEADLINE',unstarted_from_group=number);break
 # Beads is checked through the project wrapper; any read/parse/pause/ownership failure stops.
 try:
  for issue in ['quoridor-4lc','quoridor-4lc.149']:
   raw=subprocess.check_output(['bash',str(root/'scripts/dev/beads.sh'),'show',issue,'--json'],env=env,text=True,timeout=10);d=json.loads(raw)[0]
   (out/(run+'-'+issue.replace('.','-')+'-current.json')).write_text(raw)
   assert d['status']=='in_progress' and 'paused-by-user' not in d['labels'],'PAUSED_OR_NOT_ACTIVE'
   if issue.endswith('.149'):assert d['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746','OWNER_CHANGED'
 except Exception as e:event('stop',reason='CONTROL_READ_OR_OWNERSHIP_REFUSED',error=str(e),unstarted_from_group=number);break
 event('before_guarded_launch',run=run,configured_games=[g['id'] for g in c['games']],source_Git=c['Git'])
 command=[sys.executable,str(tool/'runner.py'),'--config',str(config),'node','--max-old-space-size=768','--max-semi-space-size=8','--no-node-snapshot',str(tool/'diagnose.cjs'),'--config',str(config)]
 job_env={**env,'SIGMA77_GIT_COMMIT':c['Git'],'SIGMA77_RUN_ID':run}
 result=subprocess.run(command,env=job_env)
 event('guarded_job_returned',run=run,exit=result.returncode)
 process=out/'runs'/(run+'.process.json')
 if not process.exists():event('stop',reason='ADMISSION_OR_LAUNCH_FAILURE_SPAWN0_OR_UNKNOWN',run=run);break
 p=json.loads(process.read_text())
 if p['remaining'] or p['unknown_adopted']:event('stop',reason='OWNED_RECOVERY_NOT_ZERO',run=run);break
 # Post-stop bulletin, preservation and restoration finish before the next job.
 try:subprocess.run([sys.executable,str(tool/'finish-group.py'),run],env=env,check=True)
 except Exception as e:event('stop',reason='POST_STOP_PRESERVATION_OR_REPORT_FAILED',run=run,error=str(e));break
 if result.returncode!=0:event('stop',reason='DEBUG_REQUIRES_INSPECTION_NOT_BLIND_RETRY',run=run);break
 event('group_stopped_saved',run=run)
else:event('all_registered_remaining_groups_attempted')
event('controller_returned',current_children_waited=True,new_heavy_forbidden_in_this_controller=True)
