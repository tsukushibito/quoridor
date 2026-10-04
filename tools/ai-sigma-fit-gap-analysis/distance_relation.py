"""NN0 descriptive relation to the fixed distance predictor; no learned new predictor."""
from pathlib import Path
import json,gzip,collections,math
D=Path('research-data/ai-sigma/frame16-fit-gap-analysis');rows=[json.loads(x)for x in gzip.open(D/'per-row.jsonl.gz','rt')];result={}
for split in ['train','validation']:
 q=[r for r in rows if r['split']==split];c=collections.Counter(r['group']for r in q);G=len(c);w=lambda r:1/(G*c[r['group']]);mean=lambda f:sum(w(r)*f(r)for r in q);dm=mean(lambda r:r['distance']);dv=mean(lambda r:(r['distance']-dm)**2);result[split]={}
 for name in q[0]['NN']:
  nm=mean(lambda r:r['NN'][name]);rv=mean(lambda r:(r['NN'][name]-r['distance']-(nm-dm))**2);cov=mean(lambda r:(r['NN'][name]-r['distance']-(nm-dm))*(r['distance']-dm));result[split][name]=dict(distance_mean=dm,NN_mean=nm,distance_variance=dv,rNN_D_centered_correlation=cov/math.sqrt(rv*dv)if rv*dv>0 else None,descriptive_N_on_D_slope=1+cov/dv if dv>0 else None,not_a_newfitted_candidate=True,NN_added=0)
(D/'distance-relation-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
