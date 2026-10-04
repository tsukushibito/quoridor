"""Thin in-memory AST instrumentation of the immutable shared trainer."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

D = Path('research-data/ai-sigma/frame15-learning-diagnostic')
T = Path('tools/ai-sigma-learning-diagnostic')
BASE = Path('tools/nnue-training/train.py')
BASE_SHA = '665848e238d6a7976b83c53b0c13cdb87f9e65f4a75329560d6a98afbe9863d3'
POINTS = [0,1,2,5,10,20,50,100,200,400]

def adapted():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    sys.path.insert(0,str(BASE.parent.resolve()))
    spec = importlib.util.spec_from_file_location('readonly_trainer',BASE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tree = ast.parse(BASE.read_text())
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='train')
    edits = {'schedule':0,'optimizer_observer':0,'row_binding':0,'record_storage':0}
    class Adapt(ast.NodeTransformer):
        def visit_If(self,node):
            self.generic_visit(node)
            if ast.unparse(node.test)=="step % cfg['evaluation']['interval'] == 0 or step == cfg['training']['steps']":
                node.test = ast.parse('step in diagnostic_points',mode='eval').body
                edits['schedule']+=1
            return node
        def visit_Expr(self,node):
            if ast.unparse(node)=='optimizer.step()':
                edits['optimizer_observer']+=1
                return ast.parse('observed_step(optimizer, model, next_step, indices, targets, predicted)').body[0]
            return self.generic_visit(node)
        def visit_Assign(self,node):
            if ast.unparse(node)=='all_inputs = inputs(rows, device)':
                edits['row_binding']+=1
                return [node,ast.parse('model.bind_rows(rows, all_inputs)').body[0]]
            return self.generic_visit(node)
        def visit_With(self,node):
            if "(out / 'history.jsonl').open('a')" in ast.unparse(node):
                edits['record_storage']+=1
                return ast.parse('observed_record(model, rows, values, record, out)').body[0]
            return self.generic_visit(node)
    function = Adapt().visit(function)
    assert edits==dict.fromkeys(edits,1),edits
    module.diagnostic_points = POINTS
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(BASE)+' [209 finite instrumentation]','exec'),module.__dict__)
    return module,edits

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--condition',choices=['lr1e-3','lr1e-4','lr1e-5']);a=p.parse_args()
    m,edits=adapted()
    if a.preflight:
        assert POINTS==[0,1,2,5,10,20,50,100,200,400]
        for path in T.glob('*.py'):ast.parse(path.read_text())
        for lr in ['lr1e-3','lr1e-4','lr1e-5']:
            cfg=m.resolve_config(D/'configs'/f'{lr}.json')
            assert cfg['training']['steps']==400 and cfg['training']['seed']==19080311
            assert cfg['model']['dropout']==0 and cfg['optimizer']['weight_decay']==0
        executable=Path('/home/vscode/.cache/inference/envs/quoridor-training/bin/python')
        assert executable.is_file()
        (D/'preflight.json').write_text(json.dumps({'PASS':True,'NN':0,'AST_edits':edits,'points':POINTS,
                'model_not_imported':True,'observer_extra_forward':0,'condition_samples':110210,
                'source_SHA':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in T.glob('*.py')},
                'argv':['absolute training Python','-B',str(T/'run.py'),'--condition','lr1e-3'],
                'newscience':'04:45Z','science_stop':'04:55Z'},indent=2)+'\n')
        print(json.dumps({'PASS':True,'NN':0,'AST_edits':edits}))
    else:
        prereg=json.loads((D/'preregister.json').read_text())
        for path,h in prereg['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
        from observer import DiagnosticModel,observed_step,observed_record
        import model
        model.Model=DiagnosticModel
        m.observed_step=observed_step;m.observed_record=observed_record
        args=argparse.Namespace(run_id='frame15-learning-diagnostic-'+a.condition+'-r1',
               config=D/'configs'/f'{a.condition}.json',set=[],data=prereg['stage_path'],dry_run=False,
               output=D/'runs',checkpoints=Path('models/experiments/nnue'),init_checkpoint=None)
        m.train(args)
        mdl=DiagnosticModel.instances[-1]
        out=Path(args.output)/args.run_id
        summary=json.loads((out/'summary.json').read_text());assert summary['all_samples']==110210 and summary['step']==400
        initial=json.loads((out/'dataset.json').read_text())['initial_state_sha256']
        assert initial=='e5d218c9750d581eab7ca6a114acaa8f3cf5bd24474e3f639280705271fc7ddb'
        observations={'condition':a.condition,'initial_tensor_SHA':initial,'batch_order_400_SHA':mdl.batch_hasher.hexdigest(),
            'optimizer_all_parameter_names':[k for k,v in mdl.named_parameters()if v.requires_grad],
            'observations':mdl.observations,'observer_extra_forward':0,'observer_extra_backward':0,
            'evaluation_points':POINTS,'witness_label_free_choice':'first12 train rowID SHA209-witness-v1, before tensor/target/loss',
            'same_minibatches_as_readonly_trainer':True}
        (out/'observer.json').write_text(json.dumps(observations,indent=2,allow_nan=False)+'\n')
