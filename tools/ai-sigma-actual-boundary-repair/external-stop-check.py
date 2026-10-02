from pathlib import Path
import json,datetime,os,hashlib
T=Path(__file__).resolve().parent;ROOT=T.parents[1];A=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-ACTUAL-BOUNDARY-REPAIR';checks=[];present=[]
old=ROOT/'.artifacts/ai-sigma/continuation-20261001/CRITIC-FAIR-STREAMING'
for p in old.glob('*.process.json'):
 r=json.loads(p.read_text())
 for z in r.get('tracked',[]):
  pid=z.get('pid');tick=z.get('start_ticks',z.get('starttick'));q=Path('/proc')/str(pid)/'stat'
  try:current=int(q.read_text().rsplit(')',1)[1].split()[19]);live=current==tick
  except (OSError,ValueError,IndexError):live=False
  checks.append({'pid':pid,'starttick':tick,'same_identity_live':live})
  if live:present.append(checks[-1])
heavy=[];excluded=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');cwd=str((p/'cwd').resolve());s=(p/'stat').read_text().rsplit(')',1)[1].split()
  # Research engine/browser jobs, not App Server or this metadata observer.
  if 'chrome-devtools-mcp' in cmd:
   excluded.append({'pid':int(p.name),'starttick':int(s[19]),'command':cmd,'reason':'connector/telemetry client; not Chrome executable or research NN job'});continue
  executable=Path(cmd.split()[0]).name if cmd.split() else ''
  if (executable in ['chrome','chromium','chrome-headless-shell'] or (executable=='node' and '/tools/ai-sigma-' in cmd) or ('nn-search' in cmd and 'runner' not in cmd)) and int(p.name)!=os.getpid():
   heavy.append({'pid':int(p.name),'starttick':int(s[19]),'PPID':int(s[1]),'state':s[0],'command':cmd,'cwd':cwd})
 except (OSError,ValueError,IndexError):pass
r={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_recorded_checks':checks,'same_identity_live':present,'heavy_candidates':heavy,'excluded_connector_clients':excluded,'gate':not present and not heavy,'scope':'current observation only; not whole duration or all host inference proof','PID':os.getpid(),'actual_go':False};(A/'external-stop-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'checks':len(checks),'present':len(present),'heavy':len(heavy),'gate':r['gate']}))
