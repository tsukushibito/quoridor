"""Resident JSONL inference; fixed d790 weights, private dynamic Torch B<=8."""
import sys,json,time,hashlib,struct,os,resource,traceback
from pathlib import Path
START=time.perf_counter()
import numpy as np
import torch
import onnxruntime as ort
import importlib.util
_spec=importlib.util.spec_from_file_location("gpu_adapter",Path(__file__).with_name("gpu-adapter.py"));_adapter=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_adapter);load,MODEL_SHA=_adapter.load,_adapter.MODEL_SHA
MODEL=Path(__file__).resolve().parents[2]/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx'
torch.set_num_threads(1);torch.set_num_interop_threads(1)
torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
IMPORT=time.perf_counter()-START
op=ort.SessionOptions();op.intra_op_num_threads=1;op.inter_op_num_threads=1;op.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
t=time.perf_counter();cpu=ort.InferenceSession(str(MODEL),op,providers=['CPUExecutionProvider']);CPUINIT=time.perf_counter()-t
assert cpu.get_providers()==['CPUExecutionProvider']
t=time.perf_counter();net=load(MODEL);LOAD=time.perf_counter()-t
t=time.perf_counter();torch.cuda.synchronize();torch.cuda.set_per_process_memory_fraction(6*1024**3/torch.cuda.get_device_properties(0).total_memory);torch.cuda.reset_peak_memory_stats();net.to('cuda');net.eval();torch.cuda.synchronize();UPLOAD=time.perf_counter()-t
SAMPLE_CAP=int(sys.argv[1]);assert 1<=SAMPLE_CAP<=40000
samples=0;calls={'cuda':0,'cpuort':0};rows={'cuda':0,'cpuort':0}
def info():
 return {'sample_cap':SAMPLE_CAP,'modelhash':MODEL_SHA,'provider':'torch-folded-dynamicB-v1','original_ONNX_batch':1,'batch_min':1,'batch_max':8,'dtype':'float32','TF32':False,'AMP':False,'torch':torch.__version__,'ORT':ort.__version__,'device':torch.cuda.get_device_name(),'threads':[torch.get_num_threads(),torch.get_num_interop_threads()],'CPU_affinity':sorted(os.sched_getaffinity(0)),'coldinit_s':{'import':IMPORT,'CPUORT_session':CPUINIT,'graph_weights':LOAD,'CUDA_upload_context':UPLOAD},'single_sample_equivalent':samples,'calls':calls.copy(),'rows':rows.copy(),'RAM_peak_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'GPU_allocated_B':torch.cuda.memory_allocated(),'GPU_reserved_B':torch.cuda.memory_reserved(),'GPU_peak_allocated_B':torch.cuda.max_memory_allocated(),'GPU_peak_reserved_B':torch.cuda.max_memory_reserved()}
def infer(req):
 global samples
 st=time.perf_counter_ns();items=req['items'];backend=req.get('backend','cuda')
 assert backend in calls and isinstance(items,list) and 1<=len(items)<=8,'BATCH_OR_BACKEND'
 ids=[r['id'] for r in items];assert all(isinstance(i,str) and 1<=len(i)<=128 for i in ids) and len(set(ids))==len(ids),'ID_DUPLICATE_OR_INVALID'
 for r in items:
  bits=r['features_bits648'];assert len(bits)==648 and all(type(v)==int and 0<=v<2**32 and (v&0x7f800000)!=0x7f800000 for v in bits),'FEATURE_SCHEMA'
 assert samples+len(items)<=SAMPLE_CAP,'SAMPLE_BUDGET'
 a=np.asarray([r['features_bits648'] for r in items],dtype=np.uint32).view(np.float32).reshape(len(items),8,9,9).copy();parsed=time.perf_counter_ns()
 samples+=len(items);rows[backend]+=len(items);calls[backend]+=1
 if backend=='cuda':
  torch.cuda.synchronize();tensor=torch.from_numpy(a).to('cuda');torch.cuda.synchronize();h=time.perf_counter_ns()
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
 return {'backend':backend,'actual_batch':len(items) if backend=='cuda' else 1,'serial_count':len(items) if backend=='cpuort' else 0,'items':result,'batchcost':{'server_before_JSON_ms':(time.perf_counter_ns()-st)/1e6,'stages':stages},'single_sample_equivalent':samples}
for line in sys.stdin:
 req={}
 try:
  req=json.loads(line);kind=req['op'];assert isinstance(req.get('request_id'),str),'REQUEST_ID'
  if kind in ('info','stop'):result=info()
  elif kind=='infer_batch':result=infer(req)
  else:raise ValueError('UNKNOWN_OP')
  response={'request_id':req['request_id'],'ok':True,'result':result}
 except Exception as e:response={'request_id':req.get('request_id'),'ok':False,'error':{'type':type(e).__name__,'message':str(e)},'single_sample_equivalent':samples}
 t=time.perf_counter_ns();json.dumps(response,separators=(',',':'));enc=(time.perf_counter_ns()-t)/1e6
 if response.get('ok') and req.get('op')=='infer_batch':response['result']['batchcost']['JSON_encode_firstpass_ms']=enc
 print(json.dumps(response,separators=(',',':')),flush=True)
 if req.get('op')=='stop':break
