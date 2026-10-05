import os,json,sys,time,hashlib,pathlib,resource,platform
import numpy as np,onnxruntime as ort,onnx
ROOT=pathlib.Path.cwd();R=ROOT/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE';M=ROOT/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';F=ROOT/'.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert h(M)=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d';assert h(F)=='206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb'
opts=ort.SessionOptions();opts.intra_op_num_threads=1;opts.inter_op_num_threads=1;opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
before=time.process_time();s=ort.InferenceSession(str(M),sess_options=opts,providers=['CPUExecutionProvider']);load=time.process_time()-before
assert s.get_providers()==['CPUExecutionProvider'];so=s.get_session_options();fixtures=json.loads(F.read_text())['fixtures'];out=[];inputlist=[]
def tids():
 return [{'tid':int(p.name),'stat':(p/'stat').read_text(),'allowed':next(x for x in (p/'status').read_text().splitlines() if x.startswith('Cpus_allowed_list:'))} for p in pathlib.Path('/proc/self/task').iterdir()]
t0=tids()
for f in fixtures:
 x=np.asarray(f['raw_features_float32'],dtype=np.float32).reshape(1,8,9,9);raw=s.run(['policy_logits','value'],{'input':x});p,v=raw
 assert p.shape==(1,136) and v.shape==(1,1) and np.isfinite(p).all() and np.isfinite(v).all() and -1<=float(v[0,0])<=1
 ix=f['canonical_legal_indices'];priors=None
 if f['terminal']['effective_result']=='ongoing':
  z=p.ravel()[ix].astype(np.float64);w=np.exp(z-z.max());w/=w.sum();priors=[{'canonical136':int(i),'prior':float(a)} for i,a in zip(ix,w)]
 b=x.astype('<f4').tobytes();inputlist.append({'id':f['id'],'features':x.ravel().tolist()});out.append({'id':f['id'],'classification':f['classification'],'input_float32_sha256':hashlib.sha256(b).hexdigest(),'policy_logits':p.ravel().tolist(),'value':float(v[0,0]),'shapes':[list(p.shape),list(v.shape)],'canonical_legal_priors':priors,'terminal':f['terminal']})
(R/('ort-'+sys.argv[1]+'.outputs.json')).write_text(json.dumps(out,separators=(',',':'))+'\n')
(R/'inputs.json').write_text(json.dumps(inputlist,separators=(',',':'))+'\n')
g=onnx.load(str(M),load_external_data=False)
attrs=[{'name':n.name,'op':n.op_type,'inputs':list(n.input),'outputs':list(n.output),'attributes':[{'name':a.name,'type':a.type,'repr':str(a)} for a in n.attribute]} for n in g.graph.node]
(R/'actual-graph-attributes.json').write_text(json.dumps(attrs,indent=2)+'\n')
meta={'python':sys.version,'numpy':np.__version__,'onnx':onnx.__version__,'onnxruntime':ort.__version__,'providers':s.get_providers(),'intra':so.intra_op_num_threads,'inter':so.inter_op_num_threads,'mode':str(so.execution_mode),'model_sha256':h(M),'fixtures_sha256':h(F),'input_name':s.get_inputs()[0].name,'affinity':list(os.sched_getaffinity(0)),'pid':os.getpid(),'tids_before':t0,'tids_after':tids(),'load_cpu_s':load,'cpu_s':time.process_time()-before,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'platform':platform.platform(),'env':{k:os.environ.get(k) for k in ['CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','BLIS_NUM_THREADS']}}
(R/('ort-'+sys.argv[1]+'.metadata.json')).write_text(json.dumps(meta,indent=2)+'\n');print({'cases':len(out),'versions':[np.__version__,ort.__version__],'outputs_sha256':h(R/('ort-'+sys.argv[1]+'.outputs.json'))})
