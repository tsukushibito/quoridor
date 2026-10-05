"""NN0 raw QF1 additive residual ridge, one fixed lambda."""
from pathlib import Path
import json,gzip,sys,hashlib,collections,time,struct
import numpy as np
R=Path.cwd();B=R/'research-data/ai-sigma/frame16-fit-gap-analysis';D=B/'raw-linear-control';reg=json.loads((D/'preregister.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in reg['bindings'].items():assert sha(p)==h,p
sys.path.insert(0,str(R/'tools/nnue-training'))
from frame14_data import load_stage,canonical_model_input
rows,stage=load_stage(reg['stage']);assert len(rows)==5901 and all(r['split']in['train','validation']for r in rows);old=[json.loads(l)for l in gzip.open(B/'residual-head-control/comparison-per-row.jsonl.gz','rt')];assert [r['id']for r in rows]==[r['id']for r in old]
X=np.zeros((5901,626),dtype=np.float64)
for i,r in enumerate(rows):
 c=canonical_model_input(r);assert c[0]=='QF1-f32-STM-v1'
 for view in range(2):
  ids=c[view+1];assert len(ids)==len(set(ids)) and all(0<=j<312 for j in ids);X[i,[view*312+j for j in ids]]=1
 X[i,624:]=[struct.unpack('<f',struct.pack('<I',bits))[0]for bits in c[3]]
tr=np.array([r['split']=='train'for r in rows]);groups=collections.Counter(r['group']for r in rows if r['split']=='train');assert len(groups)==96 and tr.sum()==4653
w=np.array([1/(96*groups[r['group']])for r in rows if r['split']=='train']);assert abs(w.sum()-1)<1e-12
mu=(w[:,None]*X[tr]).sum(0);var=(w[:,None]*(X[tr]-mu)**2).sum(0);zero=var<=0;mu32=mu.astype(np.float32);sigma32=np.sqrt(var).astype(np.float32);safe=sigma32.copy();safe[zero]=1;Z=((X.astype(np.float32)-mu32)/safe).astype(np.float32);Z[:,zero]=0
F=np.column_stack([np.ones(5901),Z.astype(np.float64)]);Dv=np.array([r['distance']for r in old],dtype=np.float32);y=np.array([r['rootmean']for r in old],dtype=np.float64);e=y-Dv.astype(np.float64);A=F[tr].T@(w[:,None]*F[tr])+np.diag([0]+[.01]*626);rhs=F[tr].T@(w*e[tr]);coef=np.linalg.solve(A,rhs);err=float(np.max(np.abs(A@coef-rhs)));assert np.isfinite(coef).all() and err<=1e-8*(1+np.max(np.abs(rhs))) and np.max(np.abs(coef[1:][zero]),initial=0)<1e-12
cf=coef.astype(np.float32);res=(cf[0]+Z@cf[1:]).astype(np.float32);unclip=(Dv+res).astype(np.float32);pred=np.clip(unclip,-1,1);assert np.isfinite(pred).all()
val=~tr;unseen=(X[tr,:624].sum(0)==0)&(X[val,:624].sum(0)>0);vgroups=collections.Counter(r['group']for r in rows if r['split']=='validation');vw=np.array([1/(24*vgroups[r['group']])for r in rows if r['split']=='validation']);hasunseen=(X[val,:624][:,unseen]>0).any(1)
(D/'coefficients.json.gz').write_bytes(gzip.compress(json.dumps(dict(lambda_fixed=.01,intercept_penalty=0,features=626,trainonly=True,mu_f64=mu.tolist(),population_var_f64=var.tolist(),mu_f32=mu32.tolist(),sigma_f32=sigma32.tolist(),zero_columns=np.where(zero)[0].tolist(),solve_coefficients_f64=coef.tolist(),applied_coefficients_f32=cf.tolist(),normal_residual_maxabs=err,condition_number=float(np.linalg.cond(A)),unobserved_train_validation_active_columns=np.where(unseen)[0].tolist(),val_rows_with_unseen_active=int(hasunseen.sum()),val_original_gameweight_unseen_rowmass=float(vw@hasunseen.astype(float)),val_original_gameweight_unseen_active_mass=float(vw@(X[val,:624][:,unseen].sum(1))),forward=0,optimizer=0)).encode(),compresslevel=6))
with gzip.open(D/'predictions.jsonl.gz','wt')as f:
 for i,r in enumerate(rows):f.write(json.dumps(dict(id=r['id'],raw_linear=float(pred[i]),unclipped=float(unclip[i])),separators=(',',':'))+'\n')
# Fixed distance2-only three-coefficient NN0 reference, same arithmetic.
Z2=Z[:,624:];F2=np.column_stack([np.ones(5901),Z2.astype(np.float64)]);A2=F2[tr].T@(w[:,None]*F2[tr])+np.diag([0,.01,.01]);rhs2=F2[tr].T@(w*e[tr]);c2=np.linalg.solve(A2,rhs2);cf2=c2.astype(np.float32);u2=(Dv+(cf2[0]+Z2@cf2[1:]).astype(np.float32)).astype(np.float32);p2=np.clip(u2,-1,1);assert np.isfinite(c2).all() and np.max(np.abs(A2@c2-rhs2))<=1e-8*(1+np.max(np.abs(rhs2)))
(D/'distance2-reference.json').write_text(json.dumps(dict(lambda_fixed=.01,trainonly=True,mu_f32=mu32[624:].tolist(),sigma_f32=sigma32[624:].tolist(),coefficients_f64=c2.tolist(),applied_f32=cf2.tolist(),zero_columns=np.where(zero[624:])[0].tolist(),normal_residual_maxabs=float(np.max(np.abs(A2@c2-rhs2))),condition_number=float(np.linalg.cond(A2)),added_forward=0),indent=2)+'\n')
# Reuse immutable decomposition in memory, retaining only raw-ridge new analysis.
for i,r in enumerate(old):r['NN']={'raw_linear':float(pred[i]),'distance2_reference':float(p2[i])}
s=(R/'tools/ai-sigma-fit-gap-analysis/analyze.py').read_text();s=s.replace("D=Path('research-data/ai-sigma/frame16-fit-gap-analysis');rows=[json.loads(x)for x in gzip.open(D/'per-row.jsonl.gz','rt')];", "")
s=s.replace("(D/'residual-analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\\n')", "(D/'residual-analysis.json.gz').write_bytes(gzip.compress((json.dumps(result,allow_nan=False)+'\\n').encode(),compresslevel=6))")
namespace=dict(D=D,rows=old,gzip=gzip);exec(compile(s,'readonly phase1 analyzer [raw ridge adaptation]','exec'),namespace);a=namespace['result'];out=dict(status='PASS',added_forward=0,total_NN_unchanged=29505,features=626,coefficients=627,lambda_fixed=.01,normal_residual_maxabs=err,zero_columns=int(zero.sum()),unseen_active_columns=int(unseen.sum()),splits={})
for split,planned in [('train',96),('validation',24)]:
 ix=np.array([r['split']==split for r in rows]);gg=collections.Counter(r['group']for r in rows if r['split']==split);ww=np.array([1/(planned*gg[r['group']])for r in rows if r['split']==split]);out['splits'][split]=dict(a['splits'][split]['raw_linear'],distance2_reference=a['splits'][split]['distance2_reference'],unclipped_rootmean_gameMSE=float(ww@((unclip[ix].astype(float)-y[ix])**2)),clipped_rows=int((np.abs(unclip[ix])>1).sum()))
(D/'result.json.gz').write_bytes(gzip.compress(json.dumps(out,allow_nan=False).encode(),compresslevel=6));print(json.dumps({k:v for k,v in out.items()if k!='splits'}));print(json.dumps({split:{k:v[k]for k in ['NN_gameMSE','distance_gameMSE','gain_games','loss_games','weighted_centered_correlation','unclipped_rootmean_gameMSE']}for split,v in out['splits'].items()}))
