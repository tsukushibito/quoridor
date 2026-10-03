"""Existing private-process held CPU session, strict f32 wire; no environment updates."""
import os,sys,json,time,resource
import numpy as np
import onnxruntime as ort
opt=ort.SessionOptions();opt.intra_op_num_threads=1;opt.inter_op_num_threads=1;opt.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
begin=time.perf_counter();session=ort.InferenceSession(sys.argv[1],sess_options=opt,providers=['CPUExecutionProvider']);init_ms=(time.perf_counter()-begin)*1000
input_name=session.get_inputs()[0].name
for line in sys.stdin:
 try:
  q=json.loads(line)
  if q['op']=='info':r={'version':ort.__version__,'numpy':np.__version__,'providers':session.get_providers(),'intra':session.get_session_options().intra_op_num_threads,'inter':session.get_session_options().inter_op_num_threads,'sequential':True,'init_ms':init_ms,'PID':os.getpid(),'affinity':sorted(os.sched_getaffinity(0)),'input':[(x.name,x.shape,x.type) for x in session.get_inputs()],'output':[(x.name,x.shape,x.type) for x in session.get_outputs()]}
  else:
   b=np.asarray(q['features_bits'],dtype=np.uint32);assert b.shape==(648,), 'FEATURE_SHAPE';f=b.view(np.float32).reshape(1,8,9,9);assert np.isfinite(f).all()
   t=time.perf_counter();cpu=time.process_time();out=session.run(None,{input_name:f});elapsed=(time.perf_counter()-t)*1000;cpu_ms=(time.process_time()-cpu)*1000
   p=next(x for x in out if x.size==136).reshape(-1);v=next(x for x in out if x.size==1).reshape(-1);assert p.dtype==v.dtype==np.float32 and np.isfinite(p).all() and np.isfinite(v).all() and abs(float(v[0]))<=1
   r={'logits':p.tolist(),'value':float(v[0]),'NN_bits':np.concatenate([p,v]).view(np.uint32).tolist(),'API_ms':elapsed,'process_CPU_ms':cpu_ms,'source_clock':'Python perf_counter elapsed; not controller epoch','ru_maxrss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
  print(json.dumps({'ok':True,'data':r},separators=(',',':')),flush=True)
 except Exception as e:print(json.dumps({'ok':False,'error':type(e).__name__+': '+str(e)}),flush=True)
