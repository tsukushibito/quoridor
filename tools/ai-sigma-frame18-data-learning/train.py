"""Dynamic authorized train/validation entry; immutable trainer adapted in memory."""
import argparse,ast,hashlib,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();BASE=R/'tools/nnue-training/train.py'
BASE_SHA='665848e238d6a7976b83c53b0c13cdb87f9e65f4a75329560d6a98afbe9863d3'
POINTS=[0,1,2,5,10,20,50,100,200,400,800,1200,2000]

def adapted():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    sys.path.insert(0,str(R/'tools/nnue-training'))
    sys.path.insert(0,str(R/'tools/ai-sigma-frame18-learning'))
    spec=importlib.util.spec_from_file_location('readonly_trainer_228',BASE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from loader import load_training_stage
    common_load=module.load_data
    def verified_load(path,policy):
        private,verification=load_training_stage(path)
        rows,info=common_load(path,policy)
        assert rows==private and not any(r['split']=='test' for r in rows)
        info['private_authorized_loader_verification']=verification
        return rows,info
    module.load_data=verified_load
    function=next(n for n in ast.parse(BASE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='train')
    edits=dict(schedule=0,step=0,bind=0,record=0,parity_charge=0)
    class Adapt(ast.NodeTransformer):
        def visit_If(self,n):
            self.generic_visit(n)
            if ast.unparse(n.test)=="step % cfg['evaluation']['interval'] == 0 or step == cfg['training']['steps']":
                n.test=ast.parse('step in diagnostic_points',mode='eval').body;edits['schedule']+=1
            return n
        def visit_Expr(self,n):
            if ast.unparse(n)=='optimizer.step()':
                edits['step']+=1;return ast.parse('observed_step(optimizer,model,next_step,indices,targets,predicted)').body[0]
            return self.generic_visit(n)
        def visit_Assign(self,n):
            if ast.unparse(n)=='all_inputs = inputs(rows, device)':
                edits['bind']+=1;return[n,ast.parse('model.bind_rows(rows,all_inputs)').body[0]]
            return self.generic_visit(n)
        def visit_With(self,n):
            if "(out / 'history.jsonl').open('a')" in ast.unparse(n):
                edits['record']+=1;return ast.parse('observed_record(model,rows,values,record,out)').body[0]
            return self.generic_visit(n)
        def visit_FunctionDef(self,n):
            self.generic_visit(n)
            if n.name=='evaluate':
                # Same initial evaluation pass performs an additional raw-reference forward.
                pos=next(i for i,z in enumerate(n.body) if isinstance(z,ast.Nonlocal))+1
                n.body.insert(pos,ast.parse('if step == 0: charge(len(rows))').body[0]);edits['parity_charge']+=1
            return n
    function=Adapt().visit(function);assert edits==dict.fromkeys(edits,1),edits
    module.diagnostic_points=POINTS
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(BASE)+' [228 dynamic scaled wrapper]','exec'),module.__dict__)
    return module,edits

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--settings');p.add_argument('--preflight',action='store_true');args=p.parse_args()
    trainer,edits=adapted()
    if args.preflight:
        print(json.dumps({'PASS':True,'AST_edits':edits,'model_imported':False,'NN':0,'points':POINTS}));sys.exit(0)
    settings=json.loads(Path(args.settings).read_text())
    for path,h in settings['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    import model,scaled_model
    model.Model=scaled_model.ScaleModel
    trainer.observed_step=scaled_model.observed_step;trainer.observed_record=scaled_model.observed_record
    ns=argparse.Namespace(run_id=settings['run_id'],config=settings['config'],set=[],data=settings['stage'],dry_run=False,
        output=settings['output'],checkpoints=settings['checkpoints'],init_checkpoint=None)
    trainer.train(ns)
    mdl=scaled_model.ScaleModel.instances[-1];out=Path(ns.output)/ns.run_id
    summary=json.loads((out/'summary.json').read_text())
    assert summary['step']==2000 and summary['status']=='max_steps'
    assert summary['all_samples']==256000+14*len(mdl.rows)
    (out/'observer.json').write_text(json.dumps({'batch_order_SHA':mdl.batch_hasher.hexdigest(),
        'all_samples_including_raw_parity':summary['all_samples'],'raw_parity_samples':mdl.parity_samples,
        'optimizer_parameter_names':[n for n,p in mdl.named_parameters()if p.requires_grad],
        'points':POINTS,'observer_additional_forward':0,'test_labels_read':False},indent=2)+'\n')
