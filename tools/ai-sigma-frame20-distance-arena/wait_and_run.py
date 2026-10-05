from pathlib import Path
import json,subprocess,sys,time,datetime
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['wait_receipt']);start=time.monotonic();deadline=datetime.datetime.fromisoformat(c['newscience_deadline'].replace('Z','+00:00')).timestamp()
while time.time()<deadline:
 s=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
 if s.get('phase')=='running' and not s.get('owned') and isinstance(s.get('next_at'),(int,float)) and s['next_at']-time.time()>=c['hard_s']+30:
  valid_loaded=False
  for path in (Path.cwd()/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92').glob('**/running-loaded.json'):
   try:
    x=json.loads(path.read_text())
    if x.get('config',{}).get('start_at')=='2026-10-05T00:51:02Z'and x['scheduler']['pid']==s['process']['pid']and str(x['scheduler']['start_ticks'])==str(s['process']['start_ticks']):valid_loaded=True
   except(KeyError,OSError,ValueError):pass
  if not valid_loaded:time.sleep(5);continue
  out.write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'control_wait_s':time.monotonic()-start,'owned':s.get('owned'),'NN':0,'command_called_once':True})+'\n')
  raise SystemExit(subprocess.call(['/usr/bin/python3','-B',str(Path(__file__).with_name('guard.py')),sys.argv[1]]))
 time.sleep(5)
out.write_text(json.dumps({'status':'NOT_STARTED','reason':'CURRENT_WINDOW_UNAVAILABLE','control_wait_s':time.monotonic()-start,'NN':0})+'\n');raise SystemExit(2)
