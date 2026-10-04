"""Freeze validation selection and evaluator before any new-test label read."""
from pathlib import Path
import datetime,hashlib,json,subprocess
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning';T=R/'tools/ai-sigma-frame18-data-learning'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
choices=[];stops=[]
for n in [192,576]:
 s=json.loads((D/f'learning-plan-v1/settings-{n}.json').read_text());r=D/'learning-runs'/s['run_id'];a=json.loads((r/'summary.json').read_text());p=D/'learning-guardian'/s['run_id']/'process.json';stop=json.loads(p.read_text())
 assert stop['exit']==0 and stop['reason']is None and stop['all_child_waited']and stop['current_exact_absent']and not stop['remaining']
 for pid,tick in stop['tracked'].items():
  pp=Path('/proc')/pid/'stat'
  if pp.exists():assert int(pp.read_text().rsplit(')',1)[1].split()[19])!=tick
 assert json.loads((r/'initial-function-parity.json').read_text())['PASS']
 choices.append((a['best_validation_mse'],s['positive_train_G'],a['best_step'],n,s));stops.append(p)
 _,G,step,n,s=min(choices)
# Fixed rule applied only to validation summaries.
_,G,step,n,s=min(choices);plan=json.loads((D/'dataset-v1/plan.json').read_text());base=json.loads((D/f'learning-plan-v1/baseline-{n}.json').read_text())
models={k:str(D/'learning-checkpoints'/s['run_id']/v)for k,v in {'candidate':'best.pt','initial':'initial.pt'}.items()}
meta=D/'dataset-v1/adapter/canonical.jsonl.gz';mask=D/'dataset-v1/adapter/fixed-maximum-mask.json'
paths=[*map(Path,models.values()),Path(s['config']),meta,mask,*stops,D/'dataset-v1/quantity-freeze.json',D/'learning-plan-v1/before-curves-selection-rule.json',D/f'learning-plan-v1/baseline-{n}.json',T/'test.py',T/'scaled_model.py',T/'learning_plan.py',T/'learn_guard.py',T/'freeze_test.py',R/'tools/nnue-training/model.py',R/'tools/nnue-training/common.py',R/'tools/nnue-training/frame14_data.py',R/'research-data/ai-sigma/frame15-input-scale-control/scale.json']
f={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'selection_rule':'min validation stage BEST; tie smaller G+ then earlierstep','selected_stage':n,'selected_G':G,'best_step':step,'validation_gameMSE':min(choices)[0],'models':models,'config':s['config'],'baseline_fit':base['fit'],'metadata':str(meta),'mask':str(mask),'planned_test_games':96,'sealed_labels':plan['sealed_test_advertised'],'test_label_values_read':False,'artifacts':{str(p):sha(p)for p in paths},'bootstrap':{'seed':2281805,'replicates':2000,'unit':'game paired fixed predictions; no refit'}}
fp=D/'candidate-freeze-v1.json';assert not fp.exists();write(fp,f)
settings=dict(freeze=str(fp),freeze_SHA=sha(fp),evaluation_out=str(D/'test-evaluation-r1'),guardian_out=str(D/'learning-guardian/test-r1'),entry='test.py',hard_s=300,sample_upper=20000,counter_file=str(D/'test-evaluation-r1/result.json'),newscience_deadline='2026-10-04T14:05:00Z',stop_deadline='2026-10-04T14:15:00Z',runtime_loaded=s['runtime_loaded'],sources={**f['artifacts'],str(fp):sha(fp)})
write(D/'test-settings-r1.json',settings)
write(D/'learning-finite-stop.json',{'UTC':f['UTC'],'all_stages_stopped':True,'stops':[{'path':str(p),'SHA':sha(p)}for p in stops],'samples':sum(json.loads(p.read_text())['samples_actual']for p in stops),'wall_s':sum(json.loads(p.read_text())['wall_s']for p in stops),'selection':{'stage':n,'step':step,'validation_gameMSE':f['validation_gameMSE']},'test_started':False})
print(json.dumps({'freeze_SHA':sha(fp),'stage':n,'step':step,'testlabels_read':False}))
