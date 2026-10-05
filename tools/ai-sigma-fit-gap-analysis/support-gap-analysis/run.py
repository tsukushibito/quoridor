"""Fixed saved predictions: cell support decomposition and conditional bootstrap."""
from pathlib import Path
import json,gzip,lzma,hashlib,collections,time
import numpy as np
R=Path.cwd();B=R/'research-data/ai-sigma/frame16-fit-gap-analysis';D=B/'support-gap-analysis';reg=json.loads((D/'preregister.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in reg['bindings'].items():assert sha(p)==h,p
old=[json.loads(l)for l in gzip.open(B/'per-row.jsonl.gz','rt')];assert len(old)==5901;OOF={r['id']:r for r in(json.loads(l)for l in lzma.decompress((B/'raw-cv-control/OOF-predictions.jsonl.xz').read_bytes()).splitlines())};full={r['id']:r for r in(json.loads(l)for l in lzma.decompress((B/'raw-cv-control/full-predictions.jsonl.xz').read_bytes()).splitlines())};assert len(OOF)==4653 and len(full)==5901
cohorts=['opening-'+str(k)for k in[8,12,16,20,24,28]];phases=['early','middle','late'];sides={};groupscore={};start=time.monotonic()
for side,split,G in [('OOF','train',96),('validation','validation',24)]:
 rows=[r for r in old if r['split']==split];counts=collections.Counter(r['group']for r in rows);assert len(counts)==G and len(rows)==(4653 if side=='OOF'else 1248);a=[]
 for r in rows:
  if side=='OOF':q=OOF[r['id']];assert q['group']==r['group'];base=q['foldD'];pred=q['pred']['1.0'];unclip=None
  else:q=full[r['id']];base=r['distance'];pred=q['selected_raw'];unclip=q['unclipped']
  e=r['rootmean']-base;corr=pred-base;w=1/(G*counts[r['group']]);a.append(dict(id=r['id'],group=r['group'],cohort=r['cohort'],phase=r['phase'],e=e,r=corr,w=w,baseline=base,prediction=pred,y=r['rootmean'],unclipped=unclip))
 def stats(q):
  mass=sum(t['w']for t in q);out=dict(rows=len(q),games=len(set(t['group']for t in q)),mass=mass)
  if not q:return dict(out,e_mean=None,e_RMS=None,r_mean=None,r_RMS=None,cross=None,conditional_gap=None,corr=None,corr_unknown='unobserved',signed_global_contribution=0)
  avg=lambda f:sum(t['w']*f(t)for t in q)/mass;em=avg(lambda t:t['e']);rm=avg(lambda t:t['r']);e2=avg(lambda t:t['e']**2);r2=avg(lambda t:t['r']**2);cross=avg(lambda t:t['e']*t['r']);ve=max(0,e2-em*em);vr=max(0,r2-rm*rm);cov=cross-em*rm;gap=r2-2*cross;bias=rm*rm-2*em*rm
  return dict(out,e_mean=em,e_RMS=float(np.sqrt(e2)),r_mean=rm,r_RMS=float(np.sqrt(r2)),cross=cross,conditional_gap=gap,corr=cov/np.sqrt(ve*vr)if ve*vr>0 else None,corr_unknown=None if ve*vr>0 else'zero variance',bias_part= bias,centered_gap=gap-bias,signed_global_contribution=mass*gap,boundary_prediction_rows=sum(abs(t['prediction'])==1 for t in q),baseline_clip_rows=sum(abs(t['baseline'])==1 for t in q))
 cells={c+'|'+p:stats([q for q in a if q['cohort']==c and q['phase']==p])for c in cohorts for p in phases};overall=stats(a);assert abs(sum(v['mass']for v in cells.values())-1)<1e-12 and abs(sum(v['signed_global_contribution']for v in cells.values())-overall['conditional_gap'])<1e-12
 by=collections.defaultdict(list)
 for t in a:by[t['group']].append(t)
 gs={g:dict(rows=len(q),paired_gap=sum(t['r']**2-2*t['e']*t['r']for t in q)/len(q),model_MSE=sum((t['prediction']-t['y'])**2 for t in q)/len(q),baseline_MSE=sum(t['e']**2 for t in q)/len(q))for g,q in by.items()};assert abs(np.mean([v['paired_gap']for v in gs.values()])-overall['conditional_gap'])<1e-12
 groupscore[side]=gs;sides[side]=dict(baseline='foldtrain-only WLS f32D'if side=='OOF'else'global train96 WLS f32D',fit_games='72 or78'if side=='OOF'else 96,overall=overall,cells=cells,unclipped_gap=None if side=='OOF'else sum(t['w']*((t['unclipped']-t['y'])**2-t['e']**2)for t in a))
parts={};composition=within=unmatched=0.
for cell in sides['OOF']['cells']:
 t=sides['OOF']['cells'][cell];v=sides['validation']['cells'][cell]
 if t['mass']>0 and v['mass']>0:
  c=(v['mass']-t['mass'])*t['conditional_gap'];z=v['mass']*(v['conditional_gap']-t['conditional_gap']);composition+=c;within+=z;parts[cell]=dict(kind='common',composition=c,within=z,unmatched=None)
 elif t['mass']>0 or v['mass']>0:
  u=v['signed_global_contribution']-t['signed_global_contribution'];unmatched+=u;parts[cell]=dict(kind='one-side-unobserved',composition=None,within=None,unmatched=u)
 else:parts[cell]=dict(kind='both unobserved',composition=None,within=None,unmatched=None)
gapdiff=sides['validation']['overall']['conditional_gap']-sides['OOF']['overall']['conditional_gap'];err=abs(composition+within+unmatched-gapdiff);assert err<1e-12
rng=np.random.default_rng(2161605);bs={};samples={}
for side in ['OOF','validation']:
 g=groupscore[side];values=np.array([g[k]['paired_gap']for k in sorted(g)]);boot=values[rng.integers(0,len(values),size=(2000,len(values)))].mean(1);samples[side]=boot;bs[side]=dict(groups=len(values),mean_paired_gap=float(values.mean()),percentile95=np.percentile(boot,[2.5,97.5]).tolist(),seed=2161605,replicates=2000,fit_and_lambda_fixed=True)
bs['gap_difference']=dict(mean=gapdiff,percentile95=np.percentile(samples['validation']-samples['OOF'],[2.5,97.5]).tolist(),independent_pool_resampling=True)
result=dict(status='PASS',cells_fixed=18,rowweight='1/(original_G*n_fullgame)',sides=sides,decomposition=dict(composition=composition,within=within,unmatched=unmatched,gap_difference=gapdiff,reconciliation_maxabs=err,cells=parts),game_fixedprediction_bootstrap=bs,pergame=groupscore,notes='conditional on saved fits and OOF3lambda selection; bootstrap does not capture full fold/selection dependence; neither independently held test nor pure causal covariate shift',NN_added=0,total_NN_unchanged=29505,fit=0,math_wall_s=time.monotonic()-start)
(D/'result.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':'),allow_nan=False).encode(),6));print(json.dumps(dict(decomposition=result['decomposition'],bootstrap=bs,NN=0),separators=(',',':')))
