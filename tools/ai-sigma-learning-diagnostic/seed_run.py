"""Fourth fixed condition; reuse stopped instrumentation without editing it."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

D=Path('research-data/ai-sigma/frame15-learning-diagnostic')
T=Path('tools/ai-sigma-learning-diagnostic')
p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');a=p.parse_args()
spec=importlib.util.spec_from_file_location('readonly_first3_adapter',T/'run.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
m,edits=original.adapted()
pr=json.loads((D/'fourth-preregister.json').read_text())
for path,h in pr['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
m.diagnostic_points=pr['points']
cfg=m.resolve_config(D/'configs/seed19080312.json')
assert cfg['training']['seed']==19080312 and cfg['optimizer']['lr']==.0001
assert cfg['training']['steps']==400 and pr['points']==[0,100,200,400]
if a.preflight:
    result={'PASS':True,'NN':0,'same_readonly_AST_edits':edits,'seed':19080312,'points':pr['points'],
            'samples':74804,'primary':'step200 minus own step0','observer_forward_backward_extra':0,
            'model_not_imported':True,'absolute_interpreter_exists':Path('/home/vscode/.cache/inference/envs/quoridor-training/bin/python').is_file()}
    (D/'fourth-preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
else:
    import observer
    observer.POINTS=pr['points']
    import model
    model.Model=observer.DiagnosticModel;m.observed_step=observer.observed_step;m.observed_record=observer.observed_record
    args=argparse.Namespace(run_id='frame15-learning-diagnostic-lr1e-4-seed19080312-r1',
         config=D/'configs/seed19080312.json',set=[],data=pr['stage_path'],dry_run=False,
         output=D/'runs',checkpoints=Path('models/experiments/nnue'),init_checkpoint=None)
    m.train(args)
    mdl=observer.DiagnosticModel.instances[-1];out=Path(args.output)/args.run_id
    summary=json.loads((out/'summary.json').read_text());assert summary['all_samples']==74804 and summary['step']==400
    original_w=json.loads(gzip.decompress((D/'runs/frame15-learning-diagnostic-lr1e-4-r1/witness.jsonl.gz').read_bytes()).splitlines()[0])
    assert mdl.witness_ids==original_w['IDs']
    observations={'condition':'lr1e-4-seed19080312','seed':19080312,
         'initial_tensor_SHA':json.loads((out/'dataset.json').read_text())['initial_state_sha256'],
         'batch_order_400_SHA':mdl.batch_hasher.hexdigest(),'evaluation_points':pr['points'],
         'observer_extra_forward':0,'observer_extra_backward':0,'observations':mdl.observations,
         'optimizer_all_parameter_names':[k for k,v in mdl.named_parameters()if v.requires_grad],
         'same_witness_IDs_as_first3':True,'joint_initial_and_sampling_seed_change':True,
         'torch_version':sys.modules['torch'].__version__,'python_version':sys.version}
    (out/'observer.json').write_text(json.dumps(observations,indent=2,allow_nan=False)+'\n')
