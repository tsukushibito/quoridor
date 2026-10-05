"""Train-game whole-pipeline CV: raw additive ridge, fixed three lambdas."""
from pathlib import Path
import json,gzip,sys,hashlib,struct,collections,time
import numpy as np
R=Path.cwd();B=R/'research-data/ai-sigma/frame16-fit-gap-analysis';D=B/'raw-cv-control';reg=json.loads((D/'preregister.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in reg['bindings'].items():assert sha(p)==h,p
sys.path.insert(0,str(R/'tools/nnue-training'))
from frame14_data import load_stage,canonical_model_input
rows,stage=load_stage(reg['stage']);assert len(rows)==5901 and all(r['split']in['train','validation']for r in rows);old=[json.loads(l)for l in gzip.open(B/'residual-head-control/comparison-per-row.jsonl.gz','rt')];assert [r['id']for r in rows]==[r['id']for r in old]
X=np.zeros((5901,626),dtype=np.float64)
for i,r in enumerate(rows):
 c=canonical_model_input(r)
 for view in range(2):
  assert len(c[1+view])==len(set(c[1+view])) and all(0<=j<312 for j in c[1+view]);X[i,[312*view+j for j in c[1+view]]]=1
 X[i,624:]=[struct.unpack('<f',struct.pack('<I',v))[0]for v in c[3]]
y=np.array([r['rootmean']for r in rows]);tr=np.array([r['split']=='train'for r in rows]);fold=np.array([reg['game_folds'].get(r['group'],-1)for r in rows]);assert tr.sum()==4653 and (fold[tr]>=0).all() and (fold[~tr]==-1).all();start=time.monotonic();trace=[];lambdas=[.01,1.,100.];oof={lam:np.zeros(tr.sum(),dtype=np.float32)for lam in lambdas};all_ix=np.where(tr)[0];oofbase=np.zeros(tr.sum(),dtype=np.float32);foldinfo=[]
def weights(ix):
 g=collections.Counter(rows[i]['group']for i in ix);return np.array([1/(len(g)*g[rows[i]['group']])for i in ix]),len(g)
def distance(ix):
 w,G=weights(ix);s=X[ix,625]-X[ix,624];sy=np.sum(w*s);ym=np.sum(w*y[ix]);var=np.sum(w*(s-sy)**2);cov=np.sum(w*(s-sy)*(y[ix]-ym));b=cov/var if var>0 else 0.;a=ym-b*sy;s32=X[:,625].astype(np.float32)-X[:,624].astype(np.float32);pred=np.clip(np.float32(a)+np.float32(b)*s32,-1,1).astype(np.float32);return pred,dict(a=float(a),b=float(b),variance=float(var),groups=G,fit_labels='foldtrain only')
def design(ix):
 w,G=weights(ix);mu=(w[:,None]*X[ix]).sum(0);var=(w[:,None]*(X[ix]-mu)**2).sum(0);zero=var<=0;mu32=mu.astype(np.float32);sigma=np.sqrt(var).astype(np.float32);safe=sigma.copy();safe[zero]=1;Z=((X.astype(np.float32)-mu32)/safe).astype(np.float32);Z[:,zero]=0;F=np.column_stack([np.ones(5901),Z.astype(np.float64)]);return F,Z,w,dict(mu_f32=mu32.tolist(),sigma_f32=sigma.tolist(),zero_columns=np.where(zero)[0].tolist(),fit_groups=G)
def fit(ix,F,Z,w,base,lam):
 A=F[ix].T@(w[:,None]*F[ix]);A+=np.diag([0]+[lam]*626);rhs=F[ix].T@(w*(y[ix]-base[ix].astype(np.float64)));coef=np.linalg.solve(A,rhs);err=float(np.max(np.abs(A@coef-rhs)));assert np.isfinite(coef).all() and err<=1e-8*(1+np.max(np.abs(rhs)));cf=coef.astype(np.float32);u=(base+(cf[0]+Z@cf[1:]).astype(np.float32)).astype(np.float32);pred=np.clip(u,-1,1);return pred,u,dict(lambda_fixed=lam,normal_residual_maxabs=err,condition_number=float(np.linalg.cond(A)),coefficients_f64=coef.tolist(),applied_f32=cf.tolist())
for k in range(5):
 train_ix=np.where(tr&(fold!=k))[0];held_ix=np.where(tr&(fold==k))[0];base,bc=distance(train_ix);F,Z,w,stats=design(train_ix);heldpos=np.where(fold[tr]==k)[0];oofbase[heldpos]=base[held_ix];unseen=(X[train_ix,:624].sum(0)==0)&(X[held_ix,:624].sum(0)>0);hw,hG=weights(held_ix);has=(X[held_ix,:624][:,unseen]>0).any(1);info=dict(fold=k,heldgroups=hG,heldrows=len(held_ix),baseline=bc,moments=stats,unseen_active_columns=np.where(unseen)[0].tolist(),unseen_rowmass_within_fold=float(hw@has.astype(float)),fits=[])
 for lam in lambdas:
  assert time.monotonic()-start<32;pred,u,c=fit(train_ix,F,Z,w,base,lam);oof[lam][heldpos]=pred[held_ix];info['fits'].append(c)
 foldinfo.append(info)
wfull,G=weights(all_ix);assert G==96;oof_mse={lam:float(wfull@((oof[lam].astype(float)-y[tr])**2))for lam in lambdas};minimum=min(oof_mse.values());chosen=max(lam for lam,v in oof_mse.items()if v<=minimum+1e-10);selection=dict(rule='OOF gameequal minimum; <=minimum+1e-10 tie picks larger lambda',OOF_gameMSE={str(k):v for k,v in oof_mse.items()},selected_lambda=chosen,endpoint=chosen in[.01,100.],val_used=False,OOF_baseline_gameMSE=float(wfull@((oofbase.astype(float)-y[tr])**2)))
base,bc=distance(all_ix);fit199=json.loads(Path(reg['distance_fit']).read_text())['fit'];pd=np.array([r['distance']for r in old],dtype=np.float32);parity=dict(a_difference=bc['a']-fit199['a'],b_difference=bc['b']-fit199['b'],prediction_maxabs=float(np.max(np.abs(base-pd))));assert parity['prediction_maxabs']<=1e-6 and max(abs(parity['a_difference']),abs(parity['b_difference']))<=1e-10,parity
F,Z,w,stats=design(all_ix);pred,unclip,fitc=fit(all_ix,F,Z,w,base,chosen);(D/'coefficients-and-folds.json.gz').write_bytes(gzip.compress(json.dumps(dict(fold_pipeline=foldinfo,selection=selection,fullbaseline=bc,baseline_parity=parity,fullmoments=stats,fullfit=fitc,fitcount=16,NN_added=0),separators=(',',':')).encode(),6))
with gzip.open(D/'OOF-predictions.jsonl.gz','wt')as f:
 for j,i in enumerate(all_ix):f.write(json.dumps(dict(id=rows[i]['id'],group=rows[i]['group'],fold=int(fold[i]),foldD=float(oofbase[j]),pred={str(l):float(oof[l][j])for l in lambdas}),separators=(',',':'))+'\n')
with gzip.open(D/'full-predictions.jsonl.gz','wt')as f:
 for i,r in enumerate(rows):f.write(json.dumps(dict(id=r['id'],selected_raw=float(pred[i]),unclipped=float(unclip[i])),separators=(',',':'))+'\n')
# Immutable matched analyzer with label-free bins, exact global game weighting.
s=(R/'tools/ai-sigma-fit-gap-analysis/analyze.py').read_text();s=s.replace("D=Path('research-data/ai-sigma/frame16-fit-gap-analysis');rows=[json.loads(x)for x in gzip.open(D/'per-row.jsonl.gz','rt')];",'');s=s.replace("(D/'residual-analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\\n')","(D/'residual-analysis.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':'),allow_nan=False).encode(),6))")
raw01={r['id']:r['raw_linear']for r in(json.loads(l)for l in gzip.open(B/'raw-linear-control/predictions.jsonl.gz','rt'))}
for i,r in enumerate(old):r['NN']={'selected_raw':float(pred[i]),'raw_01':raw01[r['id']]}
ns=dict(D=D,rows=old,gzip=gzip);exec(compile(s,'readonly analyzer [CV full fit]','exec'),ns);a=ns['result'];OOF={}
for lam in lambdas:
 by=collections.defaultdict(list)
 for j,i in enumerate(all_ix):by[rows[i]['group']].append((i,j))
 pg={g:dict(rows=len(v),MSE=float(np.mean([(float(oof[lam][j])-y[i])**2 for i,j in v])),baselineMSE=float(np.mean([(float(oofbase[j])-y[i])**2 for i,j in v])))for g,v in by.items()};assert abs(np.mean([v['MSE']for v in pg.values()])-oof_mse[lam])<1e-12
 dims={}
 for dim in ['phase','cohort','walls_bin']:
  groups=collections.defaultdict(list)
  for j,i in enumerate(all_ix):groups[str(old[i][dim])].append((i,j,wfull[j]))
  dims[dim]={k:dict(rows=len(v),games=len(set(rows[i]['group']for i,j,w in v)),mass=sum(w for i,j,w in v),NN_signedgap=sum(w*((float(oof[lam][j])-y[i])**2-(float(oofbase[j])-y[i])**2)for i,j,w in v))for k,v in groups.items()};assert abs(sum(q['NN_signedgap']for q in dims[dim].values())-(oof_mse[lam]-selection['OOF_baseline_gameMSE']))<1e-12
 OOF[str(lam)]=dict(gameMSE=oof_mse[lam],rowMSE=float(np.mean((oof[lam].astype(float)-y[tr])**2)),pergame=pg,label_free_bins=dims)
result=dict(status='PASS',NN_added=0,total_NN=29505,selection=selection,OOF=OOF,fullmetrics=a['splits'],baseline_parity=parity,math_wall_s=time.monotonic()-start,unclipped_fit={})
for split in ['train','validation']:
 ix=np.where(np.array([r['split']==split for r in rows]))[0];ww,GG=weights(ix);result['unclipped_fit'][split]=dict(gameMSE=float(ww@((unclip[ix].astype(float)-y[ix])**2)),cliprows=int((np.abs(unclip[ix])>1).sum()),groups=GG)
(D/'result.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':'),allow_nan=False).encode(),6));print(json.dumps(dict(selection=selection,baseline_parity=parity,metrics={s:{n:m['NN_gameMSE']for n,m in mm.items()}for s,mm in a['splits'].items()},NN=0)))
