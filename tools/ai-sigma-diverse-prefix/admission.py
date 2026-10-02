"""Fail-closed job admission; called before runner creates any owned job child."""
import datetime,json,os,time
from pathlib import Path

def classify_process(record):
 if not isinstance(record,dict) or not all(k in record for k in ['pid','ppid','start_ticks','exe','argv','state']):raise RuntimeError('PROCESS_PARSE_UNKNOWN')
 if record['state']=='Z':return False
 exe=Path(record['exe']).name;args=record['argv']
 if not isinstance(args,list) or any(not isinstance(a,str) for a in args):raise RuntimeError('ARGV_PARSE_UNKNOWN')
 renderer=exe in ['chrome','chromium','chrome-headless-shell'] and '--type=renderer' in args
 runner=exe.startswith('python') and any(Path(a).name in ['runner.py','supervise.py'] for a in args)
 cargo=exe=='cargo' and any(a in ['build','rustc'] for a in args)
 return renderer or runner or cargo

def scan_processes(exclude=None,proc=Path('/proc'),timeout=3):
 start=time.monotonic();records=[]
 for p in proc.iterdir():
  if not p.name.isdigit() or int(p.name) in (exclude or set()):continue
  if time.monotonic()-start>timeout:raise RuntimeError('ADMISSION_READ_TIMEOUT')
  try:
   fields=(p/'stat').read_text().rsplit(')',1)[1].split()
   args=[x.decode(errors='strict') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
   state=fields[0];pid=int(p.name);tick=int(fields[19]);ppid=int(fields[1])
   if not args:
    if state=='Z':continue
    raise RuntimeError('LIVE_COMMAND_UNKNOWN '+p.name)
   rec={'pid':pid,'ppid':ppid,'start_ticks':tick,'state':state,'exe':args[0],'argv':args[1:]}
   if classify_process(rec):records.append(rec)
  except (FileNotFoundError,ProcessLookupError):
   if p.exists():raise RuntimeError('ADMISSION_PROCESS_READ_UNKNOWN '+p.name)
  except Exception as error:raise RuntimeError('ADMISSION_READ_ERROR '+p.name+' '+type(error).__name__) from error
 return records

def decide(heavy,previous,error=None):
 if error:raise RuntimeError(error)
 if heavy:raise RuntimeError('EXTERNAL_HEAVY_PRESENT')
 for d in previous:
  if not isinstance(d,dict) or 'remaining' not in d or 'unknown_adopted' not in d:raise RuntimeError('OLD_STOP_UNKNOWN')
  if d['remaining'] or d['unknown_adopted']:raise RuntimeError('OLD_STOP_UNCONFIRMED')
 return True

def admit(config,out,tool,runs):
 previous=[json.loads(p.read_text()) for p in runs.glob('prefix119-*.process.json')]
 # Do not count paused metadata/MCP readers or our parent shell's command text as compute.
 heavy=scan_processes(exclude={os.getpid()}) if config['kind']!='protocol' else []
 decide(heavy,previous)
 game_records=[json.loads(p.read_text()) for p in runs.glob('prefix119-*.game-count.json')]
 if config['kind']=='browser-pair':
  if len(game_records)!=sum(d['phase']=='browser-pair' for d in previous):raise RuntimeError('GAME_COUNT_UNKNOWN')
  if sum(d['games_started'] for d in game_records)+len(config['games'])>16:raise RuntimeError('GAME_START_CAP')
 now=datetime.datetime.now(datetime.timezone.utc)
 if now>=datetime.datetime.fromisoformat(config['newjob_deadline']):raise RuntimeError('ADMISSION_DEADLINE')
 allocated=0
 for base in [out,tool,tool.parents[1]/'research-data/ai-sigma/119-diverse-prefix']:
  for p in base.rglob('*'):
   try:
    if p.is_file():allocated+=p.stat().st_blocks*512
   except FileNotFoundError:pass
 forecast=0 if config['kind']=='protocol' else config['forecast_bytes']
 if allocated+forecast>=config['new_saved_guard']:raise RuntimeError('ADMISSION_HEADROOM')
 heavy_used=sum((datetime.datetime.fromisoformat(d['end'])-datetime.datetime.fromisoformat(d['start'])).total_seconds() for d in previous if d['phase']!='protocol')
 if config['kind']!='protocol' and heavy_used+config['minimum_remaining_heavy_seconds']>3600:raise RuntimeError('ADMISSION_HEAVY_BUDGET')
 return {'UTC':now.isoformat(),'external_heavy':heavy,'prior_runs':len(previous),'prior_remaining_unknown':0,'current_allocated':allocated,'forecast':forecast,'guard':config['new_saved_guard'],'heavy_used_seconds':heavy_used,'remaining_heavy_seconds':3600-heavy_used,'previous_game_starts':sum(d['games_started'] for d in game_records),'planned_new_games':len(config.get('games',[])),'decision':'launch_allowed','location':'runner sole-root branch before subprocess.Popen; any exception means launch0'}
