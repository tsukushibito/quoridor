"""Authorized 144-equivalent local synthetic sensitivity; no training."""
import ast,gzip,hashlib,json,sys
from pathlib import Path
D=Path('research-data/ai-sigma/frame15-learning-diagnostic')
P=D/'probe-source-preregister.json'
reg=json.loads(P.read_text())
for name,digest in reg['sources'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
for entry in reg['checkpoints']:assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['SHA']
if '--preflight' in sys.argv:
 ast.parse(Path(__file__).read_text());print(json.dumps({'NN':0,'PASS':True,'absolute_interpreter':Path(reg['interpreter']).is_file(),'forward108_backward36':True}));sys.exit(0)
sys.path.insert(0,str(Path('tools/nnue-training').resolve()))
import torch
from common import load_data
from model import Model,inputs
torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
rows,info=load_data(reg['stage'],'error')
w=json.loads(next(iter(gzip.open(D/'runs/frame15-learning-diagnostic-lr1e-4-r1/witness.jsonl.gz','rt'))))
byid={r['id']:r for r in rows if r['split']=='train'};selected=[byid[i]for i in w['IDs']];assert len(selected)==12
x,d,side=inputs(selected);direction=torch.tensor([-1.,1.]);delta=1/160
out=[];count=0
for entry in reg['checkpoints']:
 cp=torch.load(entry['path'],map_location='cpu',weights_only=True);model=Model(cp['model_config']);model.load_state_dict(cp['model']);model.eval()
 for parameter in model.parameters():parameter.requires_grad_(False)
 tensor_sha=lambda:hashlib.sha256(b''.join(v.numpy().tobytes()for v in model.state_dict().values())).hexdigest()
 before=tensor_sha();captured={}
 hooks=[model.h.register_forward_hook(lambda m,i,o:captured.update(h=o.detach().clone())),model.out.register_forward_hook(lambda m,i,o:captured.update(pre=o.detach().clone()))]
 dd=d.clone().requires_grad_(True);base=model(x,dd,side);count+=12;base_h=captured['h'];base_pre=captured['pre'].flatten()
 gradient=torch.autograd.grad(base.sum(),dd)[0];count+=12
 with torch.inference_mode():
  plus=model(x,d+delta*direction,side);count+=12;plus_h=captured['h']
  minus=model(x,d-delta*direction,side);count+=12;minus_h=captured['h']
 fd=(plus-minus)/(2*delta);ad=(gradient*direction).sum(1)
 assert torch.isfinite(fd).all()and torch.isfinite(gradient).all()
 assert tensor_sha()==before
 for hook in hooks:hook.remove()
 rec={'checkpoint':entry,'tensor_SHA':before,'weights_unchanged':True,'rows':[]}
 for j,row in enumerate(selected):
  rec['rows'].append({'id':row['id'],'distance':d[j].tolist(),'base':base[j].item(),'plus':plus[j].item(),'minus':minus[j].item(),'finite_difference_directional':fd[j].item(),'input_gradient':gradient[j].tolist(),'analytic_directional':ad[j].item(),'fd_minus_analytic':(fd[j]-ad[j]).item(),'hidden_crossing_units':int(((plus_h[j]>0)!=(minus_h[j]>0)).sum()),'hidden_base_zero_units':int((base_h[j]<=0).sum()),'pre_tanh':base_pre[j].item(),'tanh_derivative':1-base[j].item()**2,'distance_fit_directional_reference':2*8.276425107422213})
 rec['summary']={'fd_mean':fd.mean().item(),'fd_RMS':fd.square().mean().sqrt().item(),'fd_min':fd.min().item(),'fd_max':fd.max().item(),'positive_count':int((fd>0).sum()),'zero_count':int((fd==0).sum()),'analytic_RMS':ad.square().mean().sqrt().item(),'maxabs_fd_minus_analytic':(fd-ad).abs().max().item(),'rows_hidden_kink':int(((plus_h>0)!=(minus_h>0)).any(1).sum())}
 out.append(rec)
assert count==144
result={'issue':'quoridor-4lc.209','samples':144,'forward_samples':108,'backward_equivalent':36,'extra_train':0,'actual_all_science_samples':405578,'raw_guard_forecast':736208,'delta_each_distance':delta,'s_direction':'self down/opponent up, s changes2delta','models':out,'PASS':True,'synthetic_off_manifold':True,'limits':['fixed12train witnesses only','not legal position reconstruction','ReLU kinks affect finite differences','local tanh saturation','sensitivity is not prediction quality or strength']}
assert not (D/'probe-result.json').exists()
(D/'probe-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({'samples':144,'summaries':[r['summary']for r in out]}))
