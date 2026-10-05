"""MAX1 faithful step0 export/parity followed by the fixed four-slot arena."""
from pathlib import Path
import sys,json,hashlib,subprocess,time,datetime,traceback
R=Path.cwd();T=Path(__file__).parent;D=R/'research-data/ai-sigma/frame20-learning-effect';c=json.loads(Path(sys.argv[1]).read_text());started=time.monotonic();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();save=lambda p,x:Path(p).write_text(json.dumps(x,indent=2)+'\n');samples=0
save(c['counter_file'],{'all_samples':0,'processed':0})
try:
 for p,h in c['sources'].items():assert sha(p)==h,p
 sys.path.insert(0,str(R/'tools/nnue-training'));sys.path.insert(0,str(R/'tools/ai-sigma-frame18-data-learning'))
 import torch,model
 from scaled_model import ScaleModel
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
 cfg=json.loads(Path(c['original_config']).read_text());assert cfg['training']['seed']==19080311
 torch.manual_seed(19080311);mdl=ScaleModel(cfg['model']);assert mdl.raw_tensor_SHA=='e5d218c9750d581eab7ca6a114acaa8f3cf5bd24474e3f639280705271fc7ddb'
 cp=torch.load(c['original_initial'],map_location='cpu',weights_only=True);assert cp['step']==0 and cp['model_config']==cfg['model'];assert all(torch.equal(v,cp['model'][k])for k,v in mdl.state_dict().items())
 names=['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias'];assert list(mdl.state_dict())==names
 packed=b''.join(mdl.state_dict()[k].detach().numpy().astype('<f4',copy=False).tobytes()for k in names);assert len(packed)==48772;assert all(torch.isfinite(v).all()for v in mdl.state_dict().values());(D/'initial.f32').write_bytes(packed)
 manifest=json.loads(Path(c['L_manifest']).read_text());manifest.update(weights=str(D/'initial.f32'),weights_SHA=sha(D/'initial.f32'),checkpoint_SHA=sha(c['original_initial']),condition='faithful228-seed19080311-step0',initial_raw_SHA=mdl.raw_tensor_SHA,initial_checkpoint_tensor_byte_PASS=True);save(D/'initial-manifest.json',manifest)
 rows=json.loads(Path(c['fixtures27']).read_text());assert len(rows)==27
 mdl.train_step=-1;mdl.eval();x,d,side=model.inputs(rows)
 with torch.inference_mode():pred=mdl(x,d,side)
 samples+=27;save(c['counter_file'],{'all_samples':samples,'processed':0});assert torch.isfinite(pred).all();save(D/'torch27.json',[{'id':r['id'],'value':v}for r,v in zip(rows,pred.tolist())])
 subprocess.run(['/home/vscode/.local/bin/node','--max-old-space-size=512',str(T/'parity.cjs'),str(D/'initial-manifest.json'),str(D/'torch27.json'),str(D/'native-parity.json')],check=True)
 parity=json.loads((D/'native-parity.json').read_text());assert parity['PASS'];samples+=parity['samples'];assert samples<=4096
 assert sha(c['L_weights'])==c['L_weights_SHA']
 subprocess.run(['/home/vscode/.local/bin/node',str(T/'model-id-fixture.cjs'),str(D/'model-id-fixture.json')],check=True)
 save(D/'model-freeze.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'L_manifest':c['L_manifest'],'L_weights_SHA':c['L_weights_SHA'],'I_weights_SHA':sha(D/'initial.f32'),'I_manifest_SHA':sha(D/'initial-manifest.json'),'scale_SHA':manifest['scale_SHA'],'config_SHA':sha(c['original_config']),'parity_samples':samples,'parity_PASS':True,'source_hashes':c['sources'],'old_test_labels_read':False,'seed':19080311,'same_initial_checkpoint_bytes':True,'tolerance':{'abs':1e-5,'rtol':1e-4}})
 save(D/'models.json',{'L':c['L_manifest'],'I':str(D/'initial-manifest.json')})
 arena={**c,'models_manifest':str(D/'models.json'),'openings':str(D/'openings4-v1.json'),'slots':[1,2,3,4],'run':'learning-effect-256-r1','preflight_NN':samples,'NNcap':363136,'processed_cap':1000000,'hands':str(D/'hands-r1.jsonl.gz')};save(D/'arena-config.json',arena)
 subprocess.run(['/home/vscode/.local/bin/node','--max-old-space-size=768',str(T/'arena.cjs'),str(D/'arena-config.json')],check=True)
 result=json.loads(Path(c['output']).read_text());result.update(initial_phase={'samples':samples,'wall_s':time.monotonic()-started-result['wholewall_ms']/1000,'parity_PASS':True,'I_weight_SHA':manifest['weights_SHA']},fit=0,optimizer=0,Torch_GPU=0,entry='learning-effect-256-v1');save(c['output'],result)
except Exception as e:
 if not Path(c['output']).exists():
  ledger=json.loads((D/'openings4-v1.json').read_text())['slots'];save(c['output'],{'task':c['task'],'schema':c['schema'],'status':'I_UNAVAILABLE_OR_PREFLIGHT_FAILED','reason':str(e),'ledger':ledger,'samples_known':samples,'unknown_inflight':True,'planned_all_slots':4,'training':0,'GPU':0})
 traceback.print_exc();raise
