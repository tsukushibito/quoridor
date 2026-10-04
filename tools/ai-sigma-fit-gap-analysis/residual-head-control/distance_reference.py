"""Prospectively added NN0 scalar-distance residual ridge reference."""
from pathlib import Path
import json,gzip,collections,hashlib,time
import numpy as np
D=Path('research-data/ai-sigma/frame16-fit-gap-analysis/residual-head-control');rows=[json.loads(l)for l in gzip.open(D/'per-row.jsonl.gz','rt')];groups=collections.Counter(r['group']for r in rows if r['split']=='train');tr=np.array([r['split']=='train'for r in rows]);s=np.array([r['opponent_distance']-r['self_distance']for r in rows],dtype=np.float32);w=np.array([1/(96*groups[r['group']])for r in rows if r['split']=='train']);mean=np.sum(w*s[tr].astype(np.float64));var=np.sum(w*(s[tr].astype(np.float64)-mean)**2);mean32=np.float32(mean);std32=np.float32(np.sqrt(var));zero=var<=0;Z=np.zeros(len(rows),dtype=np.float32)if zero else(s-mean32)/std32
X=np.column_stack([np.ones(len(rows)),Z.astype(np.float64)]);dv=np.array([r['distance']for r in rows],dtype=np.float32);e=np.array([r['rootmean']for r in rows])-dv.astype(np.float64);A=X[tr].T@(w[:,None]*X[tr])+np.diag([0,.01]);rhs=X[tr].T@(w*e[tr]);coef=np.linalg.solve(A,rhs);assert np.isfinite(coef).all();cf=coef.astype(np.float32);assert not zero or abs(cf[1])<1e-12
res=(cf[0]+cf[1]*Z).astype(np.float32);unclipped=(dv+res).astype(np.float32);pred=np.clip(unclipped,-1,1)
with gzip.open(D/'comparison-per-row.jsonl.gz','wt')as f:
 for i,r in enumerate(rows):
  r['NN']['distance_recalibration']=float(pred[i]);r['distance_reference_unclipped']=float(unclipped[i]);f.write(json.dumps(r,separators=(',',':'))+'\n')
(D/'distance-reference-coefficients.json').write_text(json.dumps(dict(lambda_fixed=.01,intercept_penalty=0,train_only=True,s='opponent-self normalized graphdistance',mean_f64=mean,var_f64=var,mean_f32=float(mean32),std_f32=float(std32),zero_variance=bool(zero),coefficients_f64=coef.tolist(),applied_f32=cf.tolist(),normal_residual_maxabs=float(np.max(np.abs(A@coef-rhs))),condition_number=float(np.linalg.cond(A)),NN_added=0),indent=2)+'\n')
