"""One frozen hidden extraction; train-only fixed ridge, no optimizer."""
from pathlib import Path
import sys,json,gzip,hashlib,time,collections
R=Path.cwd();BASE=R/'research-data/ai-sigma/frame16-fit-gap-analysis';D=BASE/'residual-head-control';reg=json.loads((D/'preregister.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in reg['bindings'].items():assert sha(p)==h,p
sys.path.insert(0,str(R/'tools/nnue-training'))
from common import load_data,measurements
from model import Model,inputs
import torch,numpy as np
torch.set_num_threads(1);torch.set_num_interop_threads(1)
rows,info=load_data(reg['stage'],'report');assert info['counts']==dict(train=4653,validation=1248);assert all(r['split']in['train','validation']for r in rows)
old=[json.loads(l)for l in gzip.open(BASE/'per-row.jsonl.gz','rt')];assert [r['id']for r in rows]==[r['id']for r in old]
x=inputs(rows);scale=json.loads(Path(reg['scale']).read_text());mu=torch.tensor(scale['mu_f32']);sigma=torch.tensor(scale['sigma_f32']);cp=torch.load(reg['checkpoint'],weights_only=True,map_location='cpu');assert cp['step']==400
mdl=Model(cp['model_config']);mdl.load_state_dict(cp['model']);mdl.eval();weight_sha=lambda:hashlib.sha256(b''.join(v.numpy().tobytes()for v in mdl.state_dict().values())).hexdigest();before=weight_sha()
H=torch.empty((5901,32),dtype=torch.float32);N=torch.empty(5901);ids=[];count=0;start=time.monotonic()
def capture(module,args):
 assert args[0].shape==(len(ids),32) and torch.isfinite(args[0]).all();H[ids]=args[0]
hook=mdl.out.register_forward_pre_hook(capture)
try:
 with torch.inference_mode():
  for split in ['train','validation']:
   ix=[i for i,r in enumerate(rows)if r['split']==split]
   for begin in range(0,len(ix),1024):
    ids=ix[begin:begin+1024];assert count+len(ids)<=5901
    N[ids]=mdl(x[0][ids],(x[1][ids]-mu)/sigma,x[2][ids]);count+=len(ids)
 hook.remove();assert count==5901 and torch.isfinite(N).all() and weight_sha()==before
 err=(N-torch.tensor([r['NN']['standard400']for r in old])).abs().max().item();assert err<=1e-6,err
 tr=[i for i,r in enumerate(rows)if r['split']=='train'];groups=collections.Counter(rows[i]['group']for i in tr);assert len(groups)==96
 w=torch.tensor([1/(96*groups[rows[i]['group']])for i in tr],dtype=torch.float64);assert abs(w.sum().item()-1)<1e-12
 ht=H[tr].double();mean64=(w[:,None]*ht).sum(0);var64=(w[:,None]*(ht-mean64)**2).sum(0);zero=var64<=0;mean=mean64.float();std=var64.sqrt().float();safe=std.clone();safe[zero]=1
 Z=(H-mean)/safe;Z[:,zero]=0;assert torch.isfinite(Z).all();X=torch.cat([torch.ones((5901,1),dtype=torch.float64),Z.double()],1)
 Dv=torch.tensor([r['distance']for r in old],dtype=torch.float32);y=torch.tensor([r['rootmean']for r in old],dtype=torch.float64);e=y-Dv.double();A=X[tr].T@(w[:,None]*X[tr]);A+=torch.diag(torch.tensor([0]+[.01]*32,dtype=torch.float64));rhs=X[tr].T@(w*e[tr]);coef=torch.linalg.solve(A,rhs)
 solve_error=(A@coef-rhs).abs().max().item();assert solve_error<=1e-8*(1+rhs.abs().max().item()) and torch.isfinite(coef).all()
 cf=coef.float();res=cf[0]+Z@cf[1:];unclipped=Dv+res;prediction=unclipped.clamp(-1,1);assert torch.isfinite(prediction).all()
 np.savez_compressed(D/'hidden_features.npz',hidden=H.numpy(),row_ids=np.array([r['id']for r in rows]))
 (D/'coefficients.json').write_text(json.dumps(dict(lambda_fixed=.01,intercept_penalty=0,rowweight='1/(96*n_game)',hidden_mean_f64=mean64.tolist(),hidden_variance_f64=var64.tolist(),hidden_mean_f32=mean.tolist(),hidden_std_f32=std.tolist(),zero_columns=zero.nonzero().flatten().tolist(),solve_coefficients_f64=coef.tolist(),applied_coefficients_f32=cf.tolist(),solve_residual_maxabs=solve_error,condition_number=torch.linalg.cond(A).item(),model_weight_SHA=before,immutable_weights=True,prediction_arithmetic='float32 residual=intercept+(Z@beta); float32 unclipped=D+residual; clamp[-1,1]',moments_fit='train-only gameequal population variance'),indent=2)+'\n')
 result=dict(status='PASS',samepass_original_prediction_maxabs=err,samples=count,training_updates=0,backward=0,model_weight_SHA=before,hidden='out pre-hook post-ReLU dropout0 eval',splits={})
 for split in ['train','validation']:
  ix=[i for i,r in enumerate(rows)if r['split']==split];ww=torch.tensor([1/(len(set(rows[i]['group']for i in ix))*sum(rows[j]['group']==rows[i]['group']for j in ix))for i in ix],dtype=torch.float64)
  result['splits'][split]=dict(ridge=measurements([rows[i]for i in ix],prediction[ix].tolist(),'rootmean',reg['constant']),standard400=measurements([rows[i]for i in ix],N[ix].tolist(),'rootmean',reg['constant']),distance=measurements([rows[i]for i in ix],Dv[ix].tolist(),'rootmean',reg['constant']),unclipped_residual_MSE=(ww*(res[ix].double()-e[ix])**2).sum().item(),unclipped_rootmean_MSE=(ww*(unclipped[ix].double()-y[ix])**2).sum().item(),clip_rows=int((unclipped[ix].abs()>1).sum()))
 with gzip.open(D/'per-row.jsonl.gz','wt')as f:
  for i,r in enumerate(old):
   q=dict(r);q['NN']=dict(ridge=prediction[i].item(),standard400=N[i].item());q['ridge_unclipped']=unclipped[i].item();f.write(json.dumps(q,separators=(',',':'))+'\n')
 (D/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result))
finally:
 (D/'actual-sample-receipt.json').write_text(json.dumps(dict(samples=count,prior_samples=23604,total_samples=23604+count,GPU=0,warm=0,training_updates=0,backward=0,test_forward=0,elapsed_s=time.monotonic()-start),indent=2)+'\n')
