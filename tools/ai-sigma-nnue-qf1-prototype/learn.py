"""One QF1-H32 rootmean-only Adam CPU trial; no extra teacher or validation selection."""
from pathlib import Path
import os,json,subprocess,hashlib,time,datetime,traceback,gzip
D=Path('research-data/ai-sigma/190-nnue-qf1-prototype')
def save(n,x):(D/n).write_text(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n')
def main():
 start=time.monotonic();pr=json.loads((D/'preregister.json').read_text())
 assert os.sched_getaffinity(0)=={8} and os.environ['CUDA_VISIBLE_DEVICES']==''
 assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(pr['newscience'].replace('Z','+00:00'))
 p=subprocess.run([pr['node'],'tools/ai-sigma-nnue-qf1-prototype/prepare.cjs'],capture_output=True,timeout=25)
 if p.returncode:raise RuntimeError(p.stderr.decode()[-4000:])
 data=json.loads(p.stdout);rows=data['samples'];assert len(rows)>0
 import numpy as np
 import torch
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.random.default_generator.manual_seed(19080311)
 class Model(torch.nn.Module):
  def __init__(self):
   super().__init__();self.ft=torch.nn.Linear(312,32);self.h=torch.nn.Linear(66,32);self.out=torch.nn.Linear(32,1)
  def forward(self,x,d,side):
   a=torch.relu(self.ft(x));p=side.long()-1;idx=torch.arange(len(x));q=torch.cat([a[idx,p],a[idx,1-p],d],1);return torch.tanh(self.out(torch.relu(self.h(q))))[:,0]
 def tensors(rs):
  x=torch.zeros(len(rs),2,312)
  for i,r in enumerate(rs):
   for p in [0,1]:x[i,p,r['ids'][p]]=1
  return x,torch.tensor([r['distance']for r in rs]),torch.tensor([r['side']for r in rs])
 x,d,side=tensors(rows);target=torch.tensor([r['rootmean']for r in rows]);tr=torch.tensor([i for i,r in enumerate(rows)if r['split']=='train']);va=[i for i,r in enumerate(rows)if r['split']=='validation'];assert len(tr)>0 and len(va)>0
 model=Model().cpu();assert all(v.dtype==torch.float32 for v in model.state_dict().values())
 counter={'sample_total':0,'train':0,'beforeafter':0,'torch_fixture':0,'native':0,'warm':0,'GPU':0}
 def charge(n,k):
  counter[k]+=n;counter['sample_total']+=n;assert counter['sample_total']<=65536;save('counter.json',counter)
 predictions={}
 charge(len(rows),'beforeafter')
 with torch.inference_mode():predictions['before']=model(x,d,side).tolist()
 opt=torch.optim.Adam(model.parameters(),lr=.001);ledger=[]
 for step in range(200):
  idx=tr[torch.randint(len(tr),(128,))];opt.zero_grad(set_to_none=True);charge(128,'train');v=model(x[idx],d[idx],side[idx]);loss=((v-target[idx])**2).mean();assert torch.isfinite(loss);loss.backward();assert all(p.grad is not None and torch.isfinite(p.grad).all()for p in model.parameters());opt.step()
  if step in [0,49,99,199]:ledger.append({'step':step+1,'rootmeanMSE':float(loss.detach())})
 charge(len(rows),'beforeafter')
 with torch.inference_mode():predictions['after']=model(x,d,side).tolist()
 assert all(np.isfinite(predictions[k]).all()for k in predictions)
 checkpoint=D/'checkpoint.pt';assert not checkpoint.exists();torch.save(model.state_dict(),checkpoint)
 state=torch.load(checkpoint,map_location='cpu',weights_only=True);assert all(torch.equal(v,state[k])for k,v in model.state_dict().items())
 pieces=[state[k].numpy().astype('<f4',copy=False).tobytes()for k in ['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias']];raw=b''.join(pieces);assert len(raw)==48772;(D/'native.f32').write_bytes(raw)
 save('weight-layout.json',{'version':'QF1-H32-f32-v1','dtype':'little-endian float32','shapes':[[32,312],[32],[32,66],[32],[1,32],[1]],'order':['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias'],'activation':'ReLU ft, ReLU hidden, tanh STM output','checkpoint_SHA256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'native_SHA256':hashlib.sha256(raw).hexdigest(),'weights_only_reload_bit_equal':True,'reload_forward':0,'quantized':False})
 mean=float(target[tr].mean());groups={}
 def aggregate(ids):
  o={'rows':len(ids),'games':len({rows[i]['group']for i in ids}),'trainmean_constant_rootmeanMSE':sum((rows[i]['rootmean']-mean)**2 for i in ids)/len(ids)}
  for name in ['before','after']:
   vals=predictions[name];eligible=[i for i in ids if rows[i]['z']is not None]
   o[name]={'rootmeanMSE':sum((vals[i]-rows[i]['rootmean'])**2 for i in ids)/len(ids),'zMSE':sum((vals[i]-rows[i]['z'])**2 for i in eligible)/len(eligible)if eligible else None,'z_rows':len(eligible),'sign_correct':sum(vals[i]*rows[i]['z']>0 for i in eligible),'saturated':sum(abs(vals[i])>=.9 for i in ids),'mean_value':sum(vals[i]for i in ids)/len(ids)}
  return o
 for g in sorted({r['group']for r in rows}):
  ix=[i for i,r in enumerate(rows)if r['group']==g];groups[g]={'split':rows[ix[0]]['split'],**aggregate(ix)}
 metrics={'train':aggregate(tr.tolist()),'validation':aggregate(va),'validation_old':aggregate([i for i in va if rows[i]['group'].startswith('native176-')]),'validation_new':aggregate([i for i in va if rows[i]['group'].startswith('native181-')]),'games':groups,'phase':{phase:aggregate([i for i in va if rows[i]['phase']==phase])for phase in ['early','middle','late']if any(rows[i]['phase']==phase for i in va)},'trainmean_constant':mean,'target':'rootmean root side-to-move K64 MCTS, not minimax','z_used_for_learning':False,'independent_holdout':False,'rootNN_not_mixed':True,'ledger':ledger,'torch':str(torch.__version__),'train_steps':200,'seed':19080311,'LR':.001,'optimizer':'Adam','parameters':sum(p.numel()for p in model.parameters()),'model':'QF1-H32','rows_denominator':2762,'reconstructed':len(rows),'masked':data['reconstruction']['masked']}
 (D/'learning.json.gz').write_bytes(gzip.compress(json.dumps(metrics,separators=(',',':'),allow_nan=False).encode(),mtime=0))
 fs=data['fixtures'];fx,fd,fp=tensors(fs);charge(len(fs),'torch_fixture')
 with torch.inference_mode():fv=model(fx,fd,fp).tolist()
 save('torch-fixtures.json',[{'id':f['id'],'value':v}for f,v in zip(fs,fv)])
 save('learn-stop.json',{'status':'PASS','wall_seconds':time.monotonic()-start,'counter':counter,'checkpoint_saved_once':True,'train_success_repeated':False,'scope_checkpoint_bytes':checkpoint.stat().st_size,'prepare_child_waited':True})
 print(json.dumps({'learning':'PASS','rows':len(rows),'samples':counter['sample_total'],'wall':time.monotonic()-start}))
if __name__=='__main__':
 try:main()
 except BaseException as e:
  save('learning-failure.json',{'typed':'SCHEMA_RESOURCE_OR_NUMERIC_UNSETTLED','error':repr(e),'traceback':traceback.format_exc()[-3000:]});raise
