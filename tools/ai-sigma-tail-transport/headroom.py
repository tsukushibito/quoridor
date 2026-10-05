import os,json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/TAIL-TRANSPORT';prior=ROOT/'.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def current(pid,tick):
 try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])==tick
 except (OSError,ValueError,IndexError):return False
ids=set()
for p in prior.glob('*.process.json'):
 d=json.loads(p.read_text())
 for r in d.get('tracked',[]):ids.add((r['pid'],r.get('start_ticks',r.get('starttick'))))
 for prefix in ['runner','child']:
  if d.get(prefix+'_pid') and d.get(prefix+'_starttick'):ids.add((d[prefix+'_pid'],d[prefix+'_starttick']))
live=[{'pid':p,'starttick':t}for p,t in sorted(ids) if current(p,t)]
heavy=[];connectors=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  exe=(p/'exe').resolve().name;cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  if exe in ['chrome','chromium','chrome_crashpad_handler']:heavy.append({'pid':int(p.name),'exe':exe,'cmd':cmd})
  elif 'chrome-devtools-mcp' in cmd:connectors.append(int(p.name))
  elif exe=='node' and ('diagnostic-arena/arena.cjs' in cmd or 'tail-transport/measure.cjs' in cmd):heavy.append({'pid':int(p.name),'exe':exe,'cmd':cmd})
 except (OSError,RuntimeError):pass
def allocated(base):
 n=0
 for p in base.rglob('*'):
  try:
   if p.is_file():n+=p.stat().st_blocks*512
  except FileNotFoundError:pass
 return n
paths={'95_stop':prior/'source-runtime-stopped-before-report.json','95_handoff':prior/'handoff-summary.json','model':ROOT/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx','wasm':ROOT/'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm'}
hashes={k:sha(p)for k,p in paths.items()}
assert hashes['95_stop']=='6111db5e75191b67f2fe04931b94eb515802096ba776c416dd33f6a1a889196a'
assert hashes['95_handoff']=='6b4af0c19ed4223fedd1b5ad937619a2297f51b0ece334dbc4f5338a01fac9d2'
assert hashes['model']=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d' and paths['model'].stat().st_size==11663428
assert hashes['wasm']=='1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'
actual=allocated(OUT)+allocated(Path(__file__).parent);forecast=22*1024*1024
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'95_process_union':len(ids),'95_live_same_identity':live,'external_heavy_detected':heavy,'devtools_connector_excluded':connectors,'model_Wasm_hashes':hashes,'current_allocated':actual,'forecast_profile_TEMP_log_raw_ending':forecast,'guard':28*1024*1024,'93_retained_allocated':allocated(ROOT/'.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA'),'headroom_sufficient':actual+forecast<28*1024*1024,'formal_no_background_CPU_guarantee':False}
(OUT/'headroom-before-NN.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not live and not heavy and result['headroom_sufficient']
