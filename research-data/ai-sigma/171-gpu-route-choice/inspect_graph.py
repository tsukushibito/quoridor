"""Static graph/weight metadata only. No torch import/session/forward/CUDA."""
import json,hashlib,collections,resource,time
from pathlib import Path
import onnx
D=Path('research-data/ai-sigma/171-gpu-route-choice')
p=Path('models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx')
t=time.time();m=onnx.load(str(p),load_external_data=False);onnx.checker.check_model(m)
def val(v):return {'name':v.name,'elem_type':v.type.tensor_type.elem_type,'shape':[x.dim_value or x.dim_param for x in v.type.tensor_type.shape.dim]}
initializers=[{'name':x.name,'dtype':x.data_type,'shape':list(x.dims),'bytes':len(x.raw_data),'raw_sha256':hashlib.sha256(x.raw_data).hexdigest(),'external':x.data_location} for x in m.graph.initializer]
nodes=[]
for n in m.graph.node:
 attrs={}
 for a in n.attribute:
  if a.type==onnx.AttributeProto.TENSOR:
   attrs[a.name]={'dtype':a.t.data_type,'shape':list(a.t.dims),'raw_sha256':hashlib.sha256(a.t.raw_data).hexdigest()}
  else:
   v=onnx.helper.get_attribute_value(a);attrs[a.name]=v.decode() if isinstance(v,bytes) else list(v) if hasattr(v,'__iter__') and not isinstance(v,str) else v
 nodes.append({'name':n.name,'op':n.op_type,'inputs':list(n.input),'outputs':list(n.output),'attrs':attrs})
sources={}
for q in [Path('.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/sources/dual_network.py'),Path('.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/sources/export_onnx.py'),Path('.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/model-manifest.json')]:
 sources[str(q)]={'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()}
out={'model':str(p),'model_bytes':p.stat().st_size,'model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'IR':m.ir_version,'opset':[{x.domain:x.version} for x in m.opset_import],'inputs':[val(x) for x in m.graph.input],'outputs':[val(x) for x in m.graph.output],'ops':dict(collections.Counter(n.op_type for n in m.graph.node)),'initializers':initializers,'nodes':nodes,'sources':sources,'elapsed_s':time.time()-t,'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'NN_modelsession_forward_CUDA':0}
(D/'graph-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('nodes','sources','initializers')}));print(json.dumps(initializers))
