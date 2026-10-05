import json,pathlib,hashlib
D=pathlib.Path(__file__).parent;A=D.parents[2]/'.artifacts/ai-sigma/resume-20261003/NNUE-FEATURE-COST';r=json.loads((A/'runs/feature156-cost-r3/result.json').read_text());fixed=json.loads((D/'fixed-actions.json').read_text());checks=[]
assert len(r['inputs'])==4
for row,p in zip(r['inputs'],fixed):
 assert row['id']==p['id'] and row['order']==p['order'] and row['actions']==len(p['actions'])
 a=row['correctness']['A']['parity_rows'];b=row['correctness']['B']['parity_rows'];assert len(a)==len(p['actions'])==len(b)
 for x,y in zip(a,b):
  for k in ['action','child_key','side','ply','distances','maps','features313','legal','terminal']:assert x[k]==y[k],(p['id'],k)
  assert len(x['features313'])==313 and all(v in [0,1] for v in x['features313']);assert all(len(m)==81 for m in x['maps'])
 for v in ['A','B']:
  m=row['repeat64'][v];assert m['branches']==len(p['actions'])*64;assert m['total_ms']>0
 assert row['repeat64']['A']['reachability_calls']==row['repeat64']['B']['reachability_calls']
 assert row['repeat64']['B']['max_changed']<=4 and row['repeat64']['B']['cache']['max_pairs']<=32
 checks.append({'id':row['id'],'children':len(a),'parity_fields_per_child':9,'exact':True})
out={'same_writer_saved_arithmetic_not_independent_verifier':True,'raw_SHA256':hashlib.sha256((A/'runs/feature156-cost-r3/result.json').read_bytes()).hexdigest(),'checks':checks,'total_children':sum(x['children'] for x in checks),'repeat64_per_variant':True,'distance_timer_missing_not_zero':all(x['repeat64'][v]['components_ms']['distance_lookup'] is None for x in r['inputs'] for v in ['A','B'])};(D/'saved-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
