"""One authorized L2 training run and no-forward weights/gate binding."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

D=Path('research-data/ai-sigma/frame14-l2-control')
R=D/'runs/frame14-l2-r1'
reg=json.loads((D/'preregister.json').read_text())
for path,h in reg['readonly_sources'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h, path
assert hashlib.sha256(Path(reg['stage']).read_bytes()).hexdigest()==reg['stage_SHA']
argv=[sys.executable,'-B','tools/nnue-training/train.py','--data',reg['stage'],'--config',str(D/'config.json'),
      '--run-id','frame14-l2-r1','--output',str(D/'runs'),'--checkpoints','models/experiments/nnue']
result=subprocess.run(argv)
if result.returncode:raise SystemExit(result.returncode)
s=json.loads((R/'summary.json').read_text());data=json.loads((R/'dataset.json').read_text())
assert data['initial_state_sha256']==reg['expected_initial_tensor_SHA']
assert s['status']=='max_steps' and s['step']==2000 and s['all_samples']==379921
assert s['last_evaluation']['train_samples_seen']==256000
baseline=Path(reg['reuse_baseline']);old=json.loads((baseline/'summary.json').read_text())
od=json.loads((baseline/'dataset.json').read_text())
assert data['validation_sha256']==od['validation_sha256'] and data['stage_manifest']==od['stage_manifest']
constant=old['last_evaluation']['validation']['constant_game_equal_mse']
import torch
torch.set_num_threads(1);torch.set_num_interop_threads(1)
weights=Path(s['checkpoint_dir']);checks={}
for name in ['initial','best','last']:
    p=weights/(name+'.pt');cp=torch.load(p,map_location='cpu',weights_only=True)
    assert cp['model_config']==json.loads((R/'config.json').read_text())['model']
    checks[name]={'path':str(p.resolve()),'checkpoint_SHA':hashlib.sha256(p.read_bytes()).hexdigest(),'B':p.stat().st_size,
                  'weight_SHA':hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes() for v in cp['model'].values())).hexdigest()}
assert checks['initial']['weight_SHA']==reg['expected_initial_tensor_SHA']
score=s['best_validation_mse'];margin=reg['gate']['margin_vs_WD0_best_and_trainconstant']
conditions={'beststep_positive':s['best_step']>0,'different_weights':checks['best']['weight_SHA']!=checks['initial']['weight_SHA'],
            'below_WD0_best_by_margin':score<=old['best_validation_mse']-margin,
            'below_trainconstant_by_margin':score<=constant-margin}
passed=all(conditions.values())
g={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':'quoridor-4lc.197',
   'status':'GATE_MET' if passed else 'GATE_NOT_MET','conditions':conditions,'margin_fixed':margin,
   'best_step':s['best_step'],'best_validation_gameMSE':score,'WD0_best_gameMSE':old['best_validation_mse'],
   'trainconstant_validation_gameMSE':constant,'trainconstant':data['constant'],'initial_SHA':reg['expected_initial_tensor_SHA'],
   'checkpoints':checks,'config_path':str((R/'config.json').resolve()),'config_SHA':hashlib.sha256((R/'config.json').read_bytes()).hexdigest(),
   'stage_SHA':reg['stage_SHA'],'validation_SHA':data['validation_sha256'],'mask_SHA':data['stage_manifest']['mask_sha256'],
   'science_samples':s['all_samples'],'train_samples':256000,'weights_reload_forward':0,
   'newtest_slots':[{'slot':i,'status':'NOT_STARTED'} for i in range(1,25)],'newtest_evaluation_samples':0,
   'oldtest_read':False,'newtest_generation_authorized_by_fixed_gate':passed,'strength_claim':False}
(D/'gate-result.json').write_text(json.dumps(g,indent=2)+'\n')
print(json.dumps(g))
