from pathlib import Path
import json,subprocess,sys,time,datetime
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['wait_receipt']);start=time.monotonic();deadline=datetime.datetime.fromisoformat(c['newscience_deadline'].replace('Z','+00:00')).timestamp()
while time.time()<deadline:
 s=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
 if s.get('phase')=='running' and s.get('next_at',0)-time.time()>=c['hard_s']+30:
  out.write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'control_wait_s':time.monotonic()-start,'owned':s.get('owned'),'NN':0,'command_called_once':True})+'\n')
  raise SystemExit(subprocess.call(['/usr/bin/python3','-B',str(Path(__file__).with_name('guard.py')),sys.argv[1]]))
 time.sleep(5)
out.write_text(json.dumps({'status':'NOT_STARTED','reason':'CURRENT_WINDOW_UNAVAILABLE','control_wait_s':time.monotonic()-start,'NN':0})+'\n');raise SystemExit(2)
