"""Fourth saved arithmetic, disjoint outputs; no model/forward."""
import csv,gzip,hashlib,io,json,sys,tarfile
from pathlib import Path
D=Path('research-data/ai-sigma/frame15-learning-diagnostic')
sys.path.insert(0,str(Path('tools/nnue-training').resolve()))
from test_contrast import interval
R=D/'runs/frame15-learning-diagnostic-lr1e-4-seed19080312-r1'
def read(p):
 return [json.loads(x) for x in gzip.open(p,'rt')]
h=read(R/'history.jsonl.gz');w=read(R/'witness.jsonl.gz');o=json.loads((R/'observer.json').read_text());s=json.loads((R/'summary.json').read_text())
assert [x['step']for x in h]==[0,100,200,400]
old=read(D/'runs/frame15-learning-diagnostic-lr1e-4-r1/history.jsonl.gz')
dist=[json.loads(x) for x in Path('research-data/ai-sigma/frame14-distance-residual/runs/frame14-distance-residual-r1/history.jsonl').read_text().splitlines()][0]
a,b=h[0],h[2];oa=old[0];ob=next(x for x in old if x['step']==200)
key='rootmean_game_equal_mse'
groups=lambda r:{g:v[key]for g,v in r['validation_games'].items()}
contrasts={'primary200_minus_own0':interval(groups(b),groups(a),seed=20980312),'primary200_minus_constant':interval(groups(b),{g:v['constant_game_equal_mse']for g,v in b['validation_games'].items()},seed=20980312),'primary200_minus_distance':interval(groups(b),groups(dist),seed=20980312)}
for x in w:
 changes=[v['prediction']-v['prediction_step0']for v in x['rows']]
 assert abs((sum(v*v for v in changes)/12)**.5-x['prediction_step0_RMS_change'])<1e-12
 assert x['IDs']==w[0]['IDs'] and len(x['IDs'])==12
for obs in o['observations']:
 for layer in obs['layers'].values():
  assert layer['gradient_all_finite'] and layer['gradient_norm']>0
  assert not layer['denominator_zero']
  assert abs(layer['actual_update_norm']/layer['weight_norm_before']-layer['update_to_weight_ratio'])<1e-12
members=[];arc=D/'fourth-weights.tar.xz';assert not arc.exists()
with tarfile.open(arc,'w:xz')as t:
 for name in ['initial.pt','best.pt','last.pt']:
  p=Path(s['checkpoint_dir'])/name;raw=p.read_bytes();info=tarfile.TarInfo(R.name+'/'+name);info.size=len(raw);info.mtime=0;t.addfile(info,io.BytesIO(raw));members.append({'member':info.name,'path':str(p),'B':len(raw),'SHA':hashlib.sha256(raw).hexdigest()})
with tarfile.open(arc,'r:xz')as t:
 for m in members:
  raw=t.extractfile(m['member']).read();assert len(raw)==m['B']and hashlib.sha256(raw).hexdigest()==m['SHA']
rows=[]
for r in h:
 rows.append({'step':r['step'],'samples_seen':r['train_samples_seen'],'epoch':r['train_epochs_equivalent'],'all_samples':r['all_samples'],'wall_s':r['elapsed_s'],**{p+'_'+k:r[p][k]for p in ['train','validation']for k in ['rootmean_mse','rootmean_game_equal_mse','z_game_equal_mse','z_sign_accuracy','saturation_fraction']}})
with (D/'fourth-curves.csv').open('w')as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
process=json.loads((D/'jobs/train-seed19080312-r1/process.json').read_text())
result={'issue':'quoridor-4lc.209','condition_count':4,'fourth':{'seed':19080312,'lr':.0001,'primary200_minus_own0':b['validation'][key]-a['validation'][key],'original_seed200_minus_own0':ob['validation'][key]-oa['validation'][key],'primary200_minus_constant':b['validation'][key]-.6787804677332444,'primary200_minus_distance':b['validation'][key]-.48514681311997876,'contrasts':contrasts,'curves':rows,'initial_tensor_SHA':o['initial_tensor_SHA'],'batch_order_SHA':o['batch_order_400_SHA'],'best_exploratory_only':s['best_step'],'process':process,'checkpoint_members':members,'archive_SHA':hashlib.sha256(arc.read_bytes()).hexdigest(),'memory_restore_PASS':True,'same12witness_PASS':True,'extra_observer_passes':0},'actual_science_samples':405434,'conservative_manager_samples':736064,'raw_counter_failure_retained':True,'probe_status':'NOT_RUN; information from fourth sufficient for next decision','new_test_or_training':0,'limits':['reused24game validation','joint initial and sampling seed change','four-condition selection','two seeds not an independent test','teacher rootmean not game strength']}
(D/'four-condition-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({'primary':result['fourth']['primary200_minus_own0'],'contrasts':contrasts,'memory_restore':True,'NN':0}))
