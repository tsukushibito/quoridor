"""Immutable settings and train-only baseline coefficients, before curves."""
from pathlib import Path
import collections,hashlib,json,struct,sys
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning';T=R/'tools/ai-sigma-frame18-data-learning'
sys.path.insert(0,str(R/'tools/ai-sigma-frame18-learning'));sys.path.insert(0,str(R/'tools/nnue-training'))
from loader import load_training_stage
from common import resolve_config,measurements
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
def distance_fit(rows):
 groups=collections.Counter(r['group']for r in rows);G=len(groups);assert G
 pts=[(1/(G*groups[r['group']]),f32(r['distance'][1]-r['distance'][0]),r['rootmean'])for r in rows]
 mx=sum(w*x for w,x,y in pts);my=sum(w*y for w,x,y in pts);var=sum(w*(x-mx)**2 for w,x,y in pts)
 b=sum(w*(x-mx)*(y-my)for w,x,y in pts)/var if var else 0.;a=my-b*mx
 return dict(a=a,b=b,a_f32=f32(a),b_f32=f32(b),constant=my,train_games=G,train_rows=len(rows),zero_variance=not var,rule='train-only gameequal WLS; f32 output clamp; no validation fit')
def distance_prediction(r,fit):
 return max(-1.,min(1.,f32(fit['a_f32']+f32(fit['b_f32']*f32(r['distance'][1]-r['distance'][0])))))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);a=p.parse_args();data=Path(a.dataset);out=D/'learning-plan-v1';assert not out.exists();out.mkdir()
 q=json.loads((data/'quantity-freeze.json').read_text());stages=[]
 paths=list(T.glob('*.py'))+[R/'tools/nnue-training/train.py',R/'tools/nnue-training/model.py',R/'tools/nnue-training/common.py',R/'tools/nnue-training/frame14_data.py',R/'tools/ai-sigma-frame18-learning/loader.py',R/'research-data/ai-sigma/frame15-input-scale-control/scale.json']
 sources={str(p):sha(p)for p in paths}
 for planned in [192,576]:
  stage=data/'adapter'/f'{planned}.stage.json';rows,verification=load_training_stage(stage);train=[r for r in rows if r['split']=='train'];fit=distance_fit(train);G=fit['train_games']
  metrics={}
  for s in ['train','validation']:
   rr=[r for r in rows if r['split']==s and(s=='train'or r.get('primary_eligible',True))]
   metrics[s]=measurements(rr,[distance_prediction(r,fit)for r in rr],'rootmean',fit['constant'])
  (out/f'baseline-{planned}.json').write_text(json.dumps({'fit':fit,'metrics':metrics,'stage_SHA':sha(stage),'testlabels_read':False},indent=2)+'\n')
  upper=256000+14*len(rows)
  cfg=resolve_config(overrides=['optimizer.lr=0.0001','optimizer.weight_decay=0','training.steps=2000','training.batch_size=128','training.seed=19080311','training.sampling="game"','training.target="rootmean"','training.threads=1','training.device="cpu"','evaluation.interval=100','evaluation.early_stopping_patience=0','data.overlap_policy="report"','limits.seconds=280','limits.samples='+str(upper)])
  config=out/f'config-{planned}.json';config.write_text(json.dumps(cfg,indent=2)+'\n');rid=f'frame18-growth228-plan{planned}-positive{G}-r1'
  s=dict(run_id=rid,stage=str(stage),config=str(config),output=str(D/'learning-runs'),checkpoints=str(D/'learning-checkpoints'),sources=dict(sources),planned_train_G=planned,positive_train_G=G,sample_upper=upper,
         guardian_out=str(D/'learning-guardian'/rid),entry='train.py',hard_s=300,counter_file=str(D/'learning-runs'/rid/'summary.json'),newscience_deadline='2026-10-04T13:40:00Z',stop_deadline='2026-10-04T13:50:00Z',runtime_loaded=str(R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame18/running-loaded.json'))
  s['sources'][str(stage)]=sha(stage);s['sources'][str(config)]=sha(config);(out/f'settings-{planned}.json').write_text(json.dumps(s,indent=2)+'\n');stages.append(s)
 assert sum(s['sample_upper']for s in stages)<2000000
 (out/'before-curves-selection-rule.json').write_text(json.dumps({'primary':'same256000 samples; shared maximumtrain OR mask','candidate':'lowest validation-primary gameMSE among stage BEST; tie smaller G+ then earlier beststep','secondary_nonselection':q['secondary_nonselection'],'fixed_points':[0,1,2,5,10,20,50,100,200,400,800,1200,2000],'stages':[{'planned':s['planned_train_G'],'G+':s['positive_train_G'],'NN_upper':s['sample_upper']}for s in stages],'test_labels_read':False,'checkpoints':'necessary private small weight payloads within authorized data scope; final archive in research Git'},indent=2)+'\n')
 print(json.dumps({'settings':str(out),'NN_upper':sum(s['sample_upper']for s in stages),'NN':0}))
