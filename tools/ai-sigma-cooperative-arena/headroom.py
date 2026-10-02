import os,json,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def allocated(base):
 total=0
 for path in base.rglob('*'):
  try:
   if path.is_file():total+=path.stat().st_blocks*512
  except FileNotFoundError:pass
 return total
heavy=[]
for path in Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  exe=(path/'exe').resolve().name
  command=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  if exe in ['chrome','chromium','chrome_crashpad_handler'] or exe=='node' and any(x in command for x in ['arena.cjs','measure.cjs','primary.cjs']):
   heavy.append({'pid':int(path.name),'exe':exe,'command':command})
 except (OSError,RuntimeError):pass
prior={}
for scope in ['TAIL-TRANSPORT','COOPERATIVE-CLOCK-INDEPENDENT']:
 identities=set()
 for path in (OUT.parent/scope).glob('*.process.json'):
  record=json.loads(path.read_text())
  for row in record.get('tracked',[]):identities.add((row['pid'],row.get('start_ticks',row.get('starttick'))))
  for kind in ['runner','child']:
   if record.get(kind+'_pid'):identities.add((record[kind+'_pid'],record[kind+'_starttick']))
 live=[]
 for pid,tick in identities:
  try:
   if int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])==tick:live.append({'pid':pid,'starttick':tick})
  except (OSError,ValueError,IndexError):pass
 prior[scope]={'recorded_identity_count':len(identities),'current_live':live}
 assert not live
files={name:ROOT/path for name,path in {
 'ONNX':'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx',
 'Wasm':'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm',
 'arena93':'tools/ai-sigma-diagnostic-arena/arena.cjs',
 'factory97':'tools/ai-sigma-tail-transport/real-backend.cjs',
 'Worker97':'tools/ai-sigma-tail-transport/early-worker.js',
 'checkpoint97':'tools/ai-sigma-tail-transport/checkpoint.js',
 'browser97':'tools/ai-sigma-tail-transport/browser.cjs',
 'page97':'tools/ai-sigma-tail-transport/early-page.js'}.items()}
hashes={name:digest(path) for name,path in files.items()}
assert hashes['ONNX']=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'
assert files['ONNX'].stat().st_size==11663428
assert hashes['Wasm']=='1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'
current=allocated(OUT)+allocated(Path(__file__).parent)+allocated(ROOT/'research-data/ai-sigma/103-cooperative-arena')
forecast=32*1024*1024 # one pair profile/TMP/public/private/monitor/ending; archive/Git reserve separate
ending=6*1024*1024
guard=56*1024*1024
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'prior':prior,'input_hashes':hashes,'input_paths':{n:str(p) for n,p in files.items()},'current_allocated':current,'next_pair_forecast':forecast,'ending_archive_Git_reserve':ending,'guard':guard,'sufficient':current+forecast+ending<guard,'formal_background_CPU_guarantee':False}
name=sys.argv[1] if len(sys.argv)>1 else 'first'
(OUT/('headroom-'+name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));assert not heavy and result['sufficient']
