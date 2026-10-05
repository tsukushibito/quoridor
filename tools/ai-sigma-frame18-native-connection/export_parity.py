"""One authorized CPU weights-only export + frozen 27 Torch/native parity."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,subprocess,sys
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-native-connection';T=R/'tools/ai-sigma-frame18-native-connection'
ap=argparse.ArgumentParser();ap.add_argument('--settings');args=ap.parse_args();s=json.loads(Path(args.settings).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in s['sources'].items():assert sha(p)==h,p
freeze=Path(s['freeze']);assert sha(freeze)=='2bac8f1f7ad87b83ac0549c01bb32eb0c8d0a2f39a05c717420e20cd668e6a60';f=json.loads(freeze.read_text());cpfile=Path(f['models']['candidate']);assert sha(cpfile)==f['artifacts'][str(cpfile)]
sys.path.insert(0,str(R/'tools/nnue-training'));sys.path.insert(0,str(R/'tools/ai-sigma-frame18-data-learning'))
import torch,model
from scaled_model import ScaleModel
torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
cfg=json.loads(Path(f['config']).read_text());torch.manual_seed(cfg['training']['seed']);cp=torch.load(cpfile,map_location='cpu',weights_only=True);assert cp['model_config']==cfg['model']
names=['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias'];shapes=[[32,312],[32],[32,66],[32],[1,32],[1]]
assert list(cp['model'])==names
packed=b''
for k,shape in zip(names,shapes):
 v=cp['model'][k];assert list(v.shape)==shape and v.dtype==torch.float32 and torch.isfinite(v).all()
 packed+=b''.join(struct.pack('<f',x)for x in v.flatten().tolist())
assert len(packed)==48772
weights=D/'candidate.f32';assert not weights.exists();weights.write_bytes(packed)
scale_path=R/'research-data/ai-sigma/frame15-input-scale-control/scale.json';assert sha(scale_path)=='68f8b43a0e4408a1546f8fa2652ffdf21f1f7bdcfbac9a25a86ac666b27aa4ee';scale=json.loads(scale_path.read_text())
manifest={'feature':'QF1-f32-STM-scaled-v1','weights':str(weights),'weights_SHA':sha(weights),'weights_B':len(packed),'checkpoint_SHA':sha(cpfile),'freeze_SHA':sha(freeze),'names':names,'shapes':shapes,'little_endian_f32':12193,'mu_f32':scale['mu_f32'],'sigma_f32':scale['sigma_f32'],'scale_SHA':sha(scale_path),'h_export_recompensation':False,'runtime':'f32((d_f32-mu_f32)/sigma_f32), actualSTM concat; no double distance swap','distance_fit':{'a':.06038215201109912,'b':7.925687690687516}}
(D/'weight-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
rows=json.loads((D/'fixed-fixtures27.json').read_text());assert len(rows)==27
mdl=ScaleModel(cfg['model']);mdl.load_state_dict(cp['model']);mdl.train_step=-1;mdl.eval();xx,dd,ss=model.inputs(rows)
with torch.inference_mode():pred=mdl(xx,dd,ss)
assert mdl.parity_samples==0 and torch.isfinite(pred).all();out=[{'id':r['id'],'value':v}for r,v in zip(rows,pred.tolist())]
(D/'torch-fixtures27.json').write_text(json.dumps(out,indent=2)+'\n')
subprocess.run(['/home/vscode/.local/bin/node','--max-old-space-size=512',str(T/'parity.cjs'),str(D/'weight-manifest.json'),str(D/'torch-fixtures27.json'),str(D/'native-parity.json')],check=True)
p=json.loads((D/'native-parity.json').read_text());total=27+p['samples'];assert total<=s['sample_upper']
(D/'parity-result.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PASS':p['PASS'],'samples':total,'Torch_samples':27,'native_samples':p['samples'],'forward_only':True,'training':0,'GPU':0,'weights_export_forward':0,'max_torch_abs':p['max_torch_abs'],'max_full_delta_abs':p['max_full_delta_abs'],'all_legal_children':p['all_legal_children']},indent=2)+'\n')
print(json.dumps({'PASS':True,'samples':total,'max_torch_abs':p['max_torch_abs'],'max_full_delta_abs':p['max_full_delta_abs']}))
