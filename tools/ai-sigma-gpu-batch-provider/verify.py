"""Recheck saved raw ID/shape/f32 bits/parity/counters and aggregate route cost, NN0."""
import json,gzip,struct,statistics,math,hashlib
from pathlib import Path
D=Path('research-data/ai-sigma/177-gpu-batch-provider')
raw=[json.loads(x) for x in gzip.decompress((D/'requests.jsonl.gz').read_bytes()).decode().splitlines()]
old=json.loads(gzip.decompress((D/'saved174-outputs.json.gz').read_bytes()))
fixtures=json.loads(Path('research-data/ai-sigma/174-gpu-inference/inputs.json').read_text())['inputs']
index={tuple(x['features_bits']):i for i,x in enumerate(fixtures)}
count=0;rows={};maxdiff={};request_ids=set()
for record in raw:
 q,r=record['request'],record['response'];assert q['request_id']==r['request_id'] and r['ok'];assert q['request_id'] not in request_ids;request_ids.add(q['request_id'])
 if q['op']!='infer_batch':continue
 assert len(q['items'])==len(r['result']['items']) and len({x['id'] for x in q['items']})==len(q['items'])
 count+=len(q['items']);assert count==r['result']['single_sample_equivalent'];rows[q['backend']]=rows.get(q['backend'],0)+len(q['items'])
 for item,out in zip(q['items'],r['result']['items']):
  assert item['id']==out['id'] and len(out['f32bits137'])==137
  vals=struct.unpack('<137f',struct.pack('<137I',*out['f32bits137']));assert all(math.isfinite(x) for x in vals) and abs(vals[-1])<=1 and list(vals)==out['logits']+[out['value']]
  i=index[tuple(item['features_bits648'])]
  if q['backend']=='cpuort':assert list(struct.unpack('<137I',struct.pack('<137f',*old[i]['CPUORT'])))==out['f32bits137'],'CPUORT_SAVED_EXACT_BITS'
  for label,ref in old[i].items():
   diff=max(abs(a-b) for a,b in zip(vals,ref));assert all(abs(a-b)<=1e-4+1e-4*abs(b) for a,b in zip(vals,ref));key=q['backend']+'-'+label;maxdiff[key]=max(diff,maxdiff.get(key,0))
assert count==305 and count<=512 and rows=={'cuda':170,'cpuort':135} and len(raw)==84
r=json.loads((D/'results.json').read_text());assert r['status']=='COMPLETED' and r['parity_pass'] and r['final_info']['single_sample_equivalent']==count
stats={}
for B,backends in r['timing'].items():
 stats[B]={}
 for name,series in backends.items():
  times=[x['total_ms'] for x in series['steady']];assert len(times)==8 and all(x>0 for x in times)
  stats[B][name]={'median_ms':statistics.median(times),'steady8_aggregate_rows_per_s':8*int(B)/(sum(times)/1000),'range_ms':[min(times),max(times)]}
 stats[B]['CPUORT_over_CUDA']=stats[B]['cpuort']['median_ms']/stats[B]['cuda']['median_ms']
print(json.dumps({'NN':0,'records':len(raw),'single_sample_equivalent':count,'rows':rows,'all_shape_finite_ID_bits_and_saved174_pass':True,'maxabs':maxdiff,'route_cost':stats,'raw_SHA':hashlib.sha256((D/'requests.jsonl.gz').read_bytes()).hexdigest()},indent=2))
