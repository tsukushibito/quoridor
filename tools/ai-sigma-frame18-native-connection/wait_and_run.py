"""Bounded background control wait; calls the science guardian at most once."""
from pathlib import Path
import datetime,json,subprocess,sys,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-native-connection';T=R/'tools/ai-sigma-frame18-native-connection'
settings=Path(sys.argv[1]);c=json.loads(settings.read_text());end=datetime.datetime.fromisoformat(c['newscience_deadline'].replace('Z','+00:00')).timestamp();begin=time.monotonic()
while time.time()<end:
 s=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text())
 if s['phase']=='running'and not s.get('recovery_required')and s['owned']is None and s['next_at']-time.time()>=c['hard_s']+30:
  (D/'search-background-wait.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'management_idle_wall_s':time.monotonic()-begin,'next_step':'one fresh guardian invocation, not automatic science rerun','LLMpolling':0},indent=2)+'\n')
  raise SystemExit(subprocess.call(['/usr/bin/python3','-B',str(T/'guard.py'),str(settings)]))
 time.sleep(5)
(D/'search-not-started.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'NOT_STARTED','reason':'CURRENT_ADMISSION_WINDOW_DEADLINE','NN':0,'idle_wall_s':time.monotonic()-begin})+'\n');raise SystemExit(1)
