from pathlib import Path
import json,tarfile,hashlib,sys,datetime
R=Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX-INDEPENDENT';D=R/'research-data/ai-sigma/119-diverse-prefix'
H=lambda b:hashlib.sha256(b).hexdigest()
i=int(sys.argv[1]);name=f'prefix119-pair{i}-r1';p=D/(name+'.tar.gz');manifest=json.loads((D/(name+'.manifest.json')).read_text());assert H(p.read_bytes())==manifest['SHA256'];by={x['path']:x['SHA256'] for x in manifest['members']};checks={str(p.relative_to(R)):manifest['SHA256']};small={}
with tarfile.open(p) as tf:
 def read(n):
  b=tf.extractfile(n).read();assert H(b)==by[n],n;checks[name+':'+n]=H(b);return json.loads(b)
 j=read(f'runs/{name}/browser-result.json');end=read(f'runs/{name}/clock-end.json');target='candidate' if i%2 else 'reference';turn=1 if i in [1,2,5,6] else 2;selected=None
 for r in j['rows']:
  d=r['diagnostic'];sample=selected is None and r['identity']['engine']==target and (1 if len(r['identity']['legal_prefix'])%2==0 else 2)==turn
  if sample:
   selected=r['identity']['request_id'];r['selected_numeric']={'numeric':d['numeric'][0],'cp':d.get('validated_cp')}
  r['diagnostic']={k:d.get(k) for k in ['identity','NN_control_events','sab_publications','validation_events','player_binding','worker_engine','control_final']}
 assert selected is not None,'NO_METADATA_SAMPLE'
 run={'run':name,'pair':i,'seed':1979,'fixture':f'diverse-prefix-{i}',**j,'clock_end':end}
 for n in [f'runs/{name}/source-bindings.json',f'runs/{name}/finally-model-drop.json',f'runs/{name}/main-timers-stop.json',f'runs/{name}/outer-controlled-stop.json',f'runs/{name}/pause-monitor-stop.json',f'runs/{name}.process.json',f'runs/{name}/finally.json']:
  if n in by:small[n]=read(n)
 (O/f'pair{i}-saved-input.json').write_text(json.dumps({'runs':[run]},separators=(',',':')))
 (O/f'pair{i}-input-checks.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_Git':manifest['source_Git'],'checks':checks,'selected':selected,'engine':target,'player':turn,'small_stop_binding':small},indent=2))
print(json.dumps({'pair':i,'compact_bytes':(O/f'pair{i}-saved-input.json').stat().st_size,'sample':selected,'member_checks':len(checks)}))
