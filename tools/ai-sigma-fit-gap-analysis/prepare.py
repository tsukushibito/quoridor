"""NN0 bindings, train-only input bins, and four required checkpoint members."""
from pathlib import Path
import json,hashlib,gzip,tarfile,sys,struct,datetime,collections
R=Path.cwd();D=R/'research-data/ai-sigma/frame16-fit-gap-analysis';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0,str(R/'tools/nnue-training'))
from common import load_data
from frame14_data import canonical_model_input
stage=R/'research-data/ai-sigma/frame14-learning/stages/train96.stage.json';rows,info=load_data(stage,'report');assert info['counts']==dict(train=4653,validation=1248)
train=[r for r in rows if r['split']=='train'];counts=collections.Counter(r['group']for r in train)
vs={'self':[],'opponent':[],'difference':[]}
for r in train:
 c=canonical_model_input(r);d=[struct.unpack('<f',struct.pack('<I',b))[0]for b in c[3]]
 for k,v in zip(vs,[d[0],d[1],d[1]-d[0]]):vs[k].append((v,1/(96*counts[r['group']])))
edges={}
for k,values in vs.items():
 values.sort();e=[]
 for p in [.2,.4,.6,.8]:
  acc=0
  for v,w in values:
   acc+=w
   if acc>=p:e.append(v);break
 edges[k]=sorted(set(e))
(D/'group-spec.json').write_text(json.dumps(dict(distance_edges=edges,fit='gameequal train-only empirical input quintiles; duplicates collapsed',labels_used=False,phase='ply<40 early;40<=ply<100 middle;100+late (shared trainer)',cohort='original opening8/12/16/20/24/28',walls='canonical STM ID290..300 selfremaining,301..311 opponentremaining; exact originalQF1 mapping; total0..4/5..9/10..14/15..20; no inferred missing',clip='fixed source A+B*(opp-self) f32 then clamp -1,1',selection='all label-free groups fixed before new perrowNN; subgroup results exploratory',train_rows=4653,train_games=96),indent=2)+'\n')
raw_root=R/'research-data/ai-sigma/frame15-learning-diagnostic';std_root=R/'research-data/ai-sigma/frame15-input-scale-control';artifacts={}
archives=[('plain',raw_root/'weights.tar.xz','frame15-learning-diagnostic-lr1e-4-r1',raw_root/'runs/frame15-learning-diagnostic-lr1e-4-r1/history.jsonl.gz'),('standard',std_root/'weights.tar.gz','models/experiments/nnue/frame15-input-scale-control-r1',std_root/'runs/frame15-input-scale-control-r1/history.jsonl.gz')]
oldmanifest=json.loads((raw_root/'weights-manifest.json').read_text());stdmanifest=json.loads((std_root/'weights-manifest.json').read_text());bindings={str(stage):sha(stage),str(raw_root/'weights-manifest.json'):sha(raw_root/'weights-manifest.json'),str(std_root/'weights-manifest.json'):sha(std_root/'weights-manifest.json')}
(D/'checkpoint-members').mkdir(exist_ok=True)
for mode,arc,prefix,hist in archives:
 bindings[str(arc)]=sha(arc);bindings[str(hist)]=sha(hist)
 with tarfile.open(arc)as t:
  for step,leaf in [(200,'best.pt'),(400,'last.pt')]:
   member=prefix+'/'+leaf;b=t.extractfile(member).read();expected=(next(x['SHA']for x in oldmanifest['members']if x['member']==member)if mode=='plain'else stdmanifest['members'][member]['SHA']);assert hashlib.sha256(b).hexdigest()==expected
   name=f'{mode}{step}';p=D/'checkpoint-members'/f'{name}.pt';p.write_bytes(b);artifacts[name]=dict(path=str(p),SHA=sha(p),mode=mode,step=step,history=str(hist),archive=str(arc),member=member)
fit=R/'research-data/ai-sigma/frame14-representation-audit/result.json';assert sha(fit)=='77ce9e79495038b25a4f4a9ffd95dc9f66700aff2c1f96cf08b65fff3c79733c';f=json.loads(fit.read_text())['fit']
reg=dict(issue='quoridor-4lc.216',UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=str(stage),stage_SHA=sha(stage),dataset_counts=info['counts'],train_groups=96,val_groups=24,artifacts=artifacts,coefficients={'a':f['a'],'b':f['b']},constant=f['constant_train_gameequal'],scale=str(std_root/'scale.json'),scale_SHA=sha(std_root/'scale.json'),forward_samples=23604,NNcap=30000,hard60=True,GPU=0,warm=0,training_updates=0,test_read=False,parity_atol=1e-6,source_bindings={**bindings,**{str(p):sha(p)for p in [fit,R/'tools/nnue-training/model.py',R/'tools/nnue-training/common.py',R/'tools/nnue-training/frame14_data.py',R/'tools/nnue-training/train.py',R/'tools/ai-sigma-qf1-distance-residual/residual_model.py',R/'tools/ai-sigma-nnue-qf1-prototype/qf1.cjs',R/'tools/nnue-training/export_generated.cjs']}})
(D/'preregister.json').write_text(json.dumps(reg,indent=2)+'\n');(D/'dataset-binding.json').write_text(json.dumps(info,indent=2)+'\n')
current=sum(p.stat().st_blocks*512 for q in [D,R/'tools/ai-sigma-fit-gap-analysis']for p in q.rglob('*')if p.is_file());pool=json.loads((R/'research-data/ai-sigma/frame15-distance-update-control/storage-admission.json').read_text())
st=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),current_owned_B=current,remaining_source_pred_plot_Git_temp_meta_forecast_B=12*1024**2,forecast_B=current+12*1024**2,guard_B=14*1024**2,reservation_B=16*1024**2,experiment_pool_B=1980*1024**2,prior_confirmed_unused_conservative_B=pool['unused_after_new8MiB'],unused_after_new16MiB=pool['unused_after_new8MiB']-16*1024**2,prior_ledger_path=str(R/'research-data/ai-sigma/frame15-distance-update-control/storage-admission.json'),old2138MiB_and2118MiB_retained=True,old_unknown_discount_B=0,parent_added_B=0,transfer_confirmed=True)
assert st['forecast_B']<st['guard_B'];(D/'storage-admission.json').write_text(json.dumps(st,indent=2)+'\n');print(json.dumps(dict(NN=0,counts=info['counts'],needed_members=4,bins=edges,forecast=st['forecast_B'])))
