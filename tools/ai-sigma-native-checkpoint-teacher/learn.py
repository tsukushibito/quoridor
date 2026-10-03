"""One fixed CPU learner connection, own game-lineage rows only; no CUDA API."""
import os,sys,json,gzip,time,hashlib,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'research-data/ai-sigma/181-checkpoint-teacher'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):(D/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def main():
 start=time.perf_counter();cfg=json.loads(Path(sys.argv[1]).read_text());pr=json.loads((D/'learner-preregister.json').read_text())
 assert os.sched_getaffinity(0)=={2} and os.environ['CUDA_VISIBLE_DEVICES']==''
 assert sha(D/'teacher-rows.jsonl.gz')==pr['dataset_SHA256']
 rows=[json.loads(x)for x in gzip.decompress((D/'teacher-rows.jsonl.gz').read_bytes()).splitlines()]
 assert all(r['lineage'].startswith('native181-train-')and '173'not in r['lineage']for r in rows)
 import numpy as np
 import torch
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.random.default_generator.manual_seed(17680311)
 class PV(torch.nn.Module):
  def __init__(self):
   super().__init__();self.hidden=torch.nn.Linear(648,32);self.policy=torch.nn.Linear(32,136);self.value=torch.nn.Linear(32,1)
  def forward(self,x):
   h=torch.relu(self.hidden(x.flatten(1)));return self.policy(h),torch.tanh(self.value(h))
 model=PV().cpu();checkpoint=D/'student-checkpoint.pt';assert not checkpoint.exists(),'NO_TRAINING_REPLACEMENT'
 x=torch.from_numpy(np.asarray([r['features648_bits']for r in rows],dtype=np.uint32).view(np.float32).copy()).reshape(-1,8,9,9)
 pi=torch.tensor([r['pi136']for r in rows],dtype=torch.float32);z=torch.tensor([[r['z_stm']if r['value_eligible']else 0]for r in rows],dtype=torch.float32)
 vm=torch.tensor([[float(r['value_eligible'])]for r in rows]);mask=torch.zeros((len(rows),136),dtype=torch.bool)
 for i,r in enumerate(rows):
  for a,k in r['mapping136']:mask[i,k]=True
 assert torch.isfinite(x).all()and torch.isfinite(pi).all()and torch.all(pi[~mask]==0)
 tr=torch.tensor([i for i,r in enumerate(rows)if r['split']=='train']);va=torch.tensor([i for i,r in enumerate(rows)if r['split']=='validation'])
 assert len(tr)>0 and len(va)>0
 def loss(idx):
  logits,value=model(x[idx]);ce=-(pi[idx]*torch.log_softmax(logits.masked_fill(~mask[idx],-1e9),dim=1)).sum(1).mean();mse=(((value-z[idx])**2)*vm[idx]).sum()/vm[idx].sum().clamp_min(1);return ce+mse,ce,mse
 def measure():
  with torch.no_grad():return {key:[float(v)for v in loss(idx)]for key,idx in [('train',tr),('validation',va)]}
 before=measure();initial=hashlib.sha256(b''.join(p.detach().numpy().tobytes()for p in model.parameters())).hexdigest();ledger=[];trainstart=time.perf_counter()
 for step in range(200):
  idx=tr[torch.randint(len(tr),(128,))];model.zero_grad(set_to_none=True);total,ce,mse=loss(idx);assert torch.isfinite(total);total.backward()
  assert all(p.grad is not None and torch.isfinite(p.grad).all()for p in model.parameters())
  if step in [0,19,49,99,199]:ledger.append({'step':step+1,'loss':float(total.detach()),'policy_CE':float(ce.detach()),'z_stm_MSE':float(mse.detach()),'gradmax':max(float(p.grad.abs().max())for p in model.parameters())})
  with torch.no_grad():
   for p in model.parameters():p.add_(p.grad,alpha=-.01)
  assert all(torch.isfinite(p).all()for p in model.parameters())
 after=measure();trainsec=time.perf_counter()-trainstart;torch.save(model.state_dict(),checkpoint)
 result={'issue':'quoridor-4lc.181','steps':200,'seed':17680311,'init_weights_SHA256':initial,'train_rows':len(tr),'validation_rows':len(va),'value_unknown_mask':0,'rootmean_auxiliary_weight':0,'loss_before':before,'loss_after':after,'ledger':ledger,'training_seconds':trainsec,'torch':str(torch.__version__),'threads':[torch.get_num_threads(),torch.get_num_interop_threads()],'dataset_SHA256':pr['dataset_SHA256'],'checkpoint_SHA256':sha(checkpoint),'teacher_fit_is_strength':False}
 save('learner-training.json',result)
 state=torch.load(checkpoint,map_location='cpu',weights_only=True);loaded=PV();loaded.load_state_dict(state,strict=True);loaded.eval();assert all(torch.equal(v,loaded.state_dict()[k])for k,v in state.items())
 idx=torch.tensor(pr['parity_indices']);sample=x[idx]
 with torch.no_grad():expected=model(sample);reloaded=loaded(sample)
 assert all(torch.equal(a,b)for a,b in zip(expected,reloaded))
 save('learner-reload.json',{'weights_only':True,'weights_bit_equal':True,'forward_bit_equal':True,'row_ids':pr['parity_row_ids']})
 import onnx,onnxruntime as ort
 exportstart=time.perf_counter();path=D/'student.onnx'
 torch.onnx.export(loaded,(sample,),str(path),input_names=['features'],output_names=['policy_logits','value'],opset_version=17,dynamo=False,dynamic_axes={'features':{0:'batch'},'policy_logits':{0:'batch'},'value':{0:'batch'}})
 onnx.checker.check_model(str(path));opt=ort.SessionOptions();opt.intra_op_num_threads=opt.inter_op_num_threads=1;opt.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
 session=ort.InferenceSession(str(path),sess_options=opt,providers=['CPUExecutionProvider']);assert ort.__version__=='1.30.0'and session.get_providers()==['CPUExecutionProvider']
 actual=session.run(None,{'features':sample.numpy()});parity=[]
 for name,ref,out in zip(['policy','value'],reloaded,actual):
  ref=ref.numpy();diff=np.abs(ref-out);tol=1e-5+1e-4*np.abs(ref);ok=bool(np.isfinite(out).all()and np.all(diff<=tol));parity.append({'output':name,'max_abs':float(diff.max()),'max_diff_over_tol':float((diff/tol).max()),'accepted':ok});assert ok,'ONNX_PARITY'
 # Dynamic batch1 is the actual arena wire. No retraining or row selection.
 for j in range(len(sample)):
  one=session.run(None,{'features':sample[j:j+1].numpy()});assert all(np.all(np.abs(v-reloaded[k][j:j+1].numpy())<=1e-5+1e-4*np.abs(reloaded[k][j:j+1].numpy()))for k,v in enumerate(one))
 save('learner-export.json',{'ONNX_SHA256':sha(path),'ORT':ort.__version__,'provider':session.get_providers(),'threads':[1,1],'parity':parity,'row_ids':pr['parity_row_ids'],'batch1_5rows_pass':True,'export_parity_seconds':time.perf_counter()-exportstart,'whole_python_seconds':time.perf_counter()-start,'formal_ready':False})
 print(json.dumps({'steps':200,'rows':len(rows),'export':True,'wall':time.perf_counter()-start}))
if __name__=='__main__':
 try:main()
 except BaseException as e:
  save('learner-failure.json',{'type':type(e).__name__,'error':str(e),'trace':traceback.format_exc()});raise
