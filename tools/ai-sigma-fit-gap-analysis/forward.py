"""One authorized four-checkpoint replay; train/val only, no updates."""
from pathlib import Path
import sys,json,gzip,hashlib,time,struct,bisect,collections
R=Path.cwd();D=R/'research-data/ai-sigma/frame16-fit-gap-analysis';reg=json.loads((D/'preregister.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in reg['source_bindings'].items():assert sha(p)==h,p
for p,h in reg.get('private_sources',{}).items():assert sha(p)==h,p
assert sha(reg['scale'])==reg['scale_SHA']
sys.path.insert(0,str(R/'tools/nnue-training'))
from common import load_data,measurements
from frame14_data import canonical_model_input
rows,info=load_data(reg['stage'],'report');assert info['counts']==dict(train=4653,validation=1248);assert all(r['split']in['train','validation']for r in rows);assert all(r['primary_eligible']for r in rows if r['split']=='validation')
import torch
from model import Model,inputs
torch.set_num_threads(1);torch.set_num_interop_threads(1);x=inputs(rows);scale=json.loads(Path(reg['scale']).read_text());mu=torch.tensor(scale['mu_f32']);sigma=torch.tensor(scale['sigma_f32']);count=0;start=time.monotonic();pred={};parity={};checkpoints={}
try:
 for name,a in reg['artifacts'].items():
  assert sha(a['path'])==a['SHA'];cp=torch.load(a['path'],weights_only=True,map_location='cpu');assert cp['step']==a['step'];mdl=Model(cp['model_config']);mdl.load_state_dict(cp['model']);mdl.eval();values=[None]*len(rows)
  checkpoints[name]=dict(step=cp['step'],weight_SHA=hashlib.sha256(b''.join(v.numpy().tobytes()for v in cp['model'].values())).hexdigest(),condition=a['mode'],model_config=cp['model_config'],standard_coordinate_weights_no_retransform=a['mode']=='standard')
  with torch.inference_mode():
   for split in ['train','validation']:
    ix=[i for i,r in enumerate(rows)if r['split']==split]
    for begin in range(0,len(ix),1024):
     ids=ix[begin:begin+1024];n=len(ids);assert count+n<=reg['NNcap']and time.monotonic()-start<55
     ds=x[1][ids];ds=(ds-mu)/sigma if a['mode']=='standard'else ds
     v=mdl(x[0][ids],ds,x[2][ids]);count+=n;assert torch.isfinite(v).all()
     for i,y in zip(ids,v.tolist()):values[i]=y
  saved=next(q for q in (json.loads(l)for l in gzip.open(a['history'],'rt'))if q['step']==a['step']);parity[name]={}
  for split in ['train','validation']:
   ix=[i for i,r in enumerate(rows)if r['split']==split];m=measurements([rows[i]for i in ix],[values[i]for i in ix],'rootmean',reg['constant']);errors={k:abs(m[k]-saved[split][k])for k in ['rootmean_mse','rootmean_game_equal_mse','z_mse','z_game_equal_mse']};assert max(errors.values())<=reg['parity_atol'],(name,split,errors);parity[name][split]=dict(PASS=True,maxabs=max(errors.values()),differences=errors,metrics=m)
  pred[name]=values
 assert count==23604
 distances=(torch.tensor(reg['coefficients']['a'],dtype=torch.float32)+torch.tensor(reg['coefficients']['b'],dtype=torch.float32)*(x[1][:,1]-x[1][:,0])).clamp(-1,1).tolist();spec=json.loads((D/'group-spec.json').read_text());bins=spec['distance_edges']
 with gzip.open(D/'per-row.jsonl.gz','wt',compresslevel=6)as f:
  for i,r in enumerate(rows):
   c=canonical_model_input(r);ids=c[1];sr=[v-290 for v in ids if 290<=v<=300];orr=[v-301 for v in ids if 301<=v<=311];assert len(sr)==len(orr)==1;walls=sr[0]+orr[0];placed=sum(162<=v<290 for v in ids);assert walls+placed==20
   ds=x[1][i].tolist();dif=ds[1]-ds[0]
   q={k:r[k]for k in ['id','group','split','cohort','ply','side','rootmean','z']};q.update(distance=distances[i],constant=reg['constant'],NN={k:v[i]for k,v in pred.items()},self_distance=ds[0],opponent_distance=ds[1],distance_difference=dif,phase='early'if r['ply']<40 else'middle'if r['ply']<100 else'late',distance_clip='saturated'if abs(distances[i])==1 else'unsaturated',self_bin=bisect.bisect_right(bins['self'],ds[0]),opponent_bin=bisect.bisect_right(bins['opponent'],ds[1]),difference_bin=bisect.bisect_right(bins['difference'],dif),walls_total=walls,walls_bin=min(3,walls//5));f.write(json.dumps(q,separators=(',',':'))+'\n')
 (D/'finite-parity.json').write_text(json.dumps(dict(PASS=True,forward_samples=count,models=parity,checkpoints=checkpoints,train_rows=4653,val_rows=1248,test_rows=0,target='rootmean STM',D_rule='Torch f32 A+B*(opponent-self), clamp',no_std_weight_retransform=True),indent=2)+'\n')
finally:
 (D/'actual-sample-receipt.json').write_text(json.dumps(dict(samples=count,GPU=0,warm=0,training_updates=0,test_forward=0,elapsed_s=time.monotonic()-start),indent=2)+'\n')
print(json.dumps(dict(samples=count,models=4,trainval_parity_PASS=True)))
