"""Resident JSONL inference; fixed d790 weights, private private dynamic Torch B<=24."""
import argparse
p=argparse.ArgumentParser();p.add_argument("--sample-cap",type=int,required=True);p.add_argument("--max-batch",type=int,default=8);args=p.parse_args();assert args.max_batch==8;assert 1<=args.sample_cap<=307200
import sys,json,time,hashlib,struct,os,resource,traceback
from pathlib import Path
START=time.perf_counter()
import numpy as np
import torch
import onnxruntime as ort
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adapter import load,MODEL_SHA
MODEL=Path.cwd()/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx'
torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
IMPORT=time.perf_counter()-START
op=ort.SessionOptions();op.intra_op_num_threads=1;op.inter_op_num_threads=1;op.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
t=time.perf_counter();cpu=ort.InferenceSession(str(MODEL),op,providers=['CPUExecutionProvider']);CPUINIT=time.perf_counter()-t
assert cpu.get_providers()==['CPUExecutionProvider']
t=time.perf_counter();net=load(MODEL);LOAD=time.perf_counter()-t
t=time.perf_counter();torch.cuda.synchronize();torch.cuda.set_per_process_memory_fraction(6*1024**3/torch.cuda.get_device_properties(0).total_memory);torch.cuda.reset_peak_memory_stats();net.to('cuda');net.eval();torch.cuda.synchronize();UPLOAD=time.perf_counter()-t
json_parse_ms=0.;json_encode_ms=0.;stdout_write_ms=0.
samples=0;startup_samples=0;capture_seconds=0.;graphs={};calls={'cuda':0,'eager':0,'cpuort':0};rows={'cuda':0,'eager':0,'cpuort':0}
# Warm and capture are inference samples and paid coldinit, not free warmup.
for B in range(1,args.max_batch+1):
 assert samples+3*B<=args.sample_cap,'STARTUP_SAMPLE_BUDGET'
 ct=time.perf_counter();static=torch.zeros((B,8,9,9),device='cuda',dtype=torch.float32)
 side=torch.cuda.Stream();side.wait_stream(torch.cuda.current_stream())
 with torch.cuda.stream(side),torch.inference_mode(),torch.autocast(device_type='cuda',enabled=False):
  for _ in range(2):
   net(static);samples+=B;startup_samples+=B
 torch.cuda.current_stream().wait_stream(side);torch.cuda.synchronize()
 graph=torch.cuda.CUDAGraph()
 with torch.cuda.graph(graph),torch.inference_mode(),torch.autocast(device_type='cuda',enabled=False):
  output=net(static)
 samples+=B;startup_samples+=B;torch.cuda.synchronize();graphs[B]=(static,graph,output);capture_seconds+=time.perf_counter()-ct
 assert torch.cuda.max_memory_reserved()<6*1024**3,'STARTUP_VRAM_GUARD'
def info():
 return {'sample_cap':args.sample_cap,'wire_totals_ms':{'json_parse':json_parse_ms,'json_encode_firstpass':json_encode_ms,'stdout_write':stdout_write_ms},'private_issue':'quoridor-4lc.221','modelhash':MODEL_SHA,'provider':'torch-folded-CUDAgraph-B1to8-v1','graph_startup_samples':startup_samples,'graph_capture_warm_seconds':capture_seconds,'captured_B':list(graphs),'original_ONNX_batch':1,'batch_min':1,'batch_max':args.max_batch,'dtype':'float32','TF32':False,'AMP':False,'torch':torch.__version__,'ORT':ort.__version__,'device':torch.cuda.get_device_name(),'threads':[torch.get_num_threads(),torch.get_num_interop_threads()],'CPU_affinity':sorted(os.sched_getaffinity(0)),'coldinit_s':{'import':IMPORT,'CPUORT_session':CPUINIT,'graph_weights':LOAD,'CUDA_upload_context':UPLOAD},'single_sample_equivalent':samples,'calls':calls.copy(),'rows':rows.copy(),'RAM_peak_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'GPU_allocated_B':torch.cuda.memory_allocated(),'GPU_reserved_B':torch.cuda.memory_reserved(),'GPU_peak_allocated_B':torch.cuda.max_memory_allocated(),'GPU_peak_reserved_B':torch.cuda.max_memory_reserved()}
def infer(req):
 global samples
 st=time.perf_counter_ns();items=req['items'];backend=req.get('backend','cuda')
 assert backend in calls and isinstance(items,list) and 1<=len(items)<=args.max_batch,'BATCH_OR_BACKEND'
 ids=[r['id'] for r in items];assert all(isinstance(i,str) and 1<=len(i)<=128 for i in ids) and len(set(ids))==len(ids),'ID_DUPLICATE_OR_INVALID'
 for r in items:
  bits=r['features_bits648'];assert len(bits)==648 and all(type(v)==int and 0<=v<2**32 and (v&0x7f800000)!=0x7f800000 for v in bits),'FEATURE_SCHEMA'
 assert samples+len(items)<=args.sample_cap,'SAMPLE_BUDGET'
 a=np.asarray([r['features_bits648'] for r in items],dtype=np.uint32).view(np.float32).reshape(len(items),8,9,9).copy();parsed=time.perf_counter_ns()
 samples+=len(items);rows[backend]+=len(items);calls[backend]+=1
 if backend in ('cuda','eager'):
  torch.cuda.synchronize()
  if backend=='cuda':
   static,graph,output=graphs[len(items)];static.copy_(torch.from_numpy(a));tensor=static
  else:tensor=torch.from_numpy(a).to('cuda')
  torch.cuda.synchronize();h=time.perf_counter_ns()
  if backend=='cuda':graph.replay();p,v=output
  else:
   with torch.inference_mode(),torch.autocast(device_type='cuda',enabled=False):p,v=net(tensor)
  torch.cuda.synchronize();f=time.perf_counter_ns();p=p.cpu().numpy().copy();v=v.cpu().numpy().copy();torch.cuda.synchronize();d=time.perf_counter_ns()
  stages={'input_parse_ms':(parsed-st)/1e6,'H2D_sync_ms':(h-parsed)/1e6,'forward_sync_ms':(f-h)/1e6,'D2H_sync_ms':(d-f)/1e6}
 else:
  pv=[cpu.run(['policy_logits','value'],{'input':a[i:i+1].copy()}) for i in range(len(items))];p=np.concatenate([x[0] for x in pv]);v=np.concatenate([x[1] for x in pv]);stages={'input_parse_ms':(parsed-st)/1e6,'CPUORT_serial_ms':(time.perf_counter_ns()-parsed)/1e6}
 assert p.shape==(len(items),136) and v.shape==(len(items),1) and np.isfinite(p).all() and np.isfinite(v).all() and np.all(np.abs(v)<=1),'OUTPUT_SCHEMA'
 assert torch.cuda.max_memory_reserved()<6*1024**3,'VRAM_GUARD'
 result=[]
 for i,id in enumerate(ids):
  vals=np.concatenate([p[i],v[i]]).astype(np.float32,copy=False);result.append({'id':id,'f32bits137':vals.view(np.uint32).tolist(),'logits':p[i].tolist(),'value':float(v[i,0])})
 return {'backend':backend,'actual_batch':len(items) if backend in ('cuda','eager') else 1,'serial_count':len(items) if backend=='cpuort' else 0,'items':result,'batchcost':{'server_before_JSON_ms':(time.perf_counter_ns()-st)/1e6,'stages':stages},'single_sample_equivalent':samples}
for line in sys.stdin:
 req={}
 try:
  jt=time.perf_counter_ns();req=json.loads(line);json_parse_ms+=(time.perf_counter_ns()-jt)/1e6;kind=req['op'];assert isinstance(req.get('request_id'),str),'REQUEST_ID'
  if kind in ('info','stop'):result=info()
  elif kind=='infer_batch':result=infer(req)
  else:raise ValueError('UNKNOWN_OP')
  response={'request_id':req['request_id'],'ok':True,'result':result}
 except Exception as e:response={'request_id':req.get('request_id'),'ok':False,'error':{'type':type(e).__name__,'message':str(e)},'single_sample_equivalent':samples}
 t=time.perf_counter_ns();json.dumps(response,separators=(',',':'));enc=(time.perf_counter_ns()-t)/1e6;json_encode_ms+=enc
 if response.get('ok') and req.get('op')=='infer_batch':response['result']['batchcost']['JSON_encode_firstpass_ms']=enc
 wt=time.perf_counter_ns();print(json.dumps(response,separators=(',',':')),flush=True);stdout_write_ms+=(time.perf_counter_ns()-wt)/1e6
 if req.get('op')=='stop':break
