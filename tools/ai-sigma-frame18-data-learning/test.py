"""One frozen new-test evaluation; never trains or changes candidate selection."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,math,random,sys,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning';T=R/'tools/ai-sigma-frame18-data-learning'
sys.path.insert(0,str(R/'tools/nnue-training'))
from common import measurements
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(s)for s in f if s.strip()]
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--settings',required=True);args=ap.parse_args()
 s=json.loads(Path(args.settings).read_text());fp=Path(s['freeze']);assert sha(fp)==s['freeze_SHA'];f=json.loads(fp.read_text())
 for p,h in f['artifacts'].items():assert sha(p)==h,p
 out=Path(s['evaluation_out']);assert not out.exists();out.mkdir()
 write(out/'access-start.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'freeze_SHA':s['freeze_SHA'],'first_test_label_access_after_freeze':True})
 meta=[r for r in rows(f['metadata'])if r['split']=='test'];mask=json.loads(Path(f['mask']).read_text())
 assert len({r['id']for r in meta})==len(meta)
 # Hash and decode only after immutable freeze verification.
 label=f['sealed_labels'];assert sha(label['path'])==label['sha256']
 lab=rows(label['path']);assert all(r['split']=='test'for r in lab)
 byid={r['id']:r for r in lab};assert len(byid)==len(lab) and set(byid)=={r['id']for r in meta}
 rr=[]
 for m in meta:
  l=byid[m['id']];assert mask['rows'][m['id']]['split']=='test' and mask['rows'][m['id']]['group']==m['group']
  for k in ['rootmean','z']:assert l[k]is None or math.isfinite(l[k])and -1<=l[k]<=1
  rr.append(dict(m,rootmean=l['rootmean'],z=l['z'],primary_eligible=mask['rows'][m['id']]['primary_eligible']))
 groups=[g for g,v in mask['games'].items()if v['split']=='test'];assert len(groups)==f['planned_test_games']
 assert {r['group']for r in rr}<={*groups}
 import torch
 import model
 from scaled_model import ScaleModel
 from learning_plan import distance_prediction
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
 cfg=json.loads(Path(f['config']).read_text());torch.manual_seed(cfg['training']['seed']);x,dist,side=model.inputs(rr)
 preds={};tensorhashes={};samples=0
 for name in ['candidate','initial']:
  cp=torch.load(f['models'][name],map_location='cpu',weights_only=True)
  assert cp['model_config']==cfg['model']
  h=hashlib.sha256(b''.join(v.numpy().tobytes()for v in cp['model'].values())).hexdigest();tensorhashes[name]=h
  reuse=next((k for k in preds if tensorhashes.get(k)==h),None)
  if reuse:preds[name]=preds[reuse];continue
  mdl=ScaleModel(cfg['model']);mdl.load_state_dict(cp['model']);mdl.train_step=-1;mdl.eval();values=[]
  with torch.inference_mode():
   for start in range(0,len(rr),1024):
    stop=min(len(rr),start+1024);y=mdl(x[start:stop],dist[start:stop],side[start:stop]);assert torch.isfinite(y).all()and(y.abs()<=1).all()
    values+=y.tolist();samples+=stop-start;assert samples<=s['sample_upper']
  assert mdl.parity_samples==0;preds[name]=values
 fit=f['baseline_fit'];preds['distance']=[distance_prediction(r,fit)for r in rr];preds['constant']=[fit['constant']]*len(rr)
 primary=[i for i,r in enumerate(rr)if r['primary_eligible']];results={};games={}
 for name,p in preds.items():
  results[name]={'primary':measurements([rr[i]for i in primary],[p[i]for i in primary],'rootmean',fit['constant']),'all_rows':measurements(rr,p,'rootmean',fit['constant'])}
  games[name]={}
  for g in groups:
   idx=[i for i in primary if rr[i]['group']==g]
   games[name][g]=measurements([rr[i]for i in idx],[p[i]for i in idx],'rootmean',fit['constant'])
 bootstrap={}
 # Fixed-fit paired game interval; no refit, lambda/selection uncertainty not covered.
 for base in ['distance','constant','initial']:
  for target in ['rootmean','z']:
   key=target+'_game_equal_mse';delta=[games['candidate'][g][key]-games[base][g][key]for g in groups if games['candidate'][g][key]is not None and games[base][g][key]is not None]
   rng=random.Random(f['bootstrap']['seed']);b=sorted(sum(rng.choices(delta,k=len(delta)))/len(delta)for _ in range(f['bootstrap']['replicates']))if delta else []
   bootstrap[base+'_'+target]={'games':len(delta),'delta':sum(delta)/len(delta)if delta else None,'percentile95':[b[int(.025*len(b))],b[min(len(b)-1,int(.975*len(b)))]]if b else None,'gain_games':sum(v<0 for v in delta)}
 with gzip.open(out/'predictions.jsonl.gz','wt')as h:
  for i,r in enumerate(rr):h.write(json.dumps({'id':r['id'],'group':r['group'],'primary_eligible':r['primary_eligible'],'rootmean':r['rootmean'],'z':r['z'],'prediction':{k:v[i]for k,v in preds.items()}})+'\n')
 write(out/'pergame.json',games)
 result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'samples':samples,'planned_test_games':len(groups),'actual_test_games':len({r['group']for r in rr}),'all_rows':len(rr),'primary_rows':len(primary),'excluded_rows':len(rr)-len(primary),'zero_eligible_games':[g for g in groups if games['candidate'][g]['rows']==0],'models':results,'weight_SHA':tensorhashes,'paired_fixedfit_bootstrap':bootstrap,'freeze_SHA':s['freeze_SHA'],'test_reselection':False,'old_test_read':False,'training':0,'strength_claim':False,'interval_limit':'conditional fixed candidate/fit; selection and teacher dependence not fully represented'}
 write(out/'result.json',result);print(json.dumps({k:result[k]for k in ['samples','planned_test_games','all_rows','primary_rows','models']}))
if __name__=='__main__':main()
