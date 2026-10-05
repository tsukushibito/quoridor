"""NN0 diagnostic: JSON codec only, no IPC/model/backend speed claim."""
import hashlib,json,resource,statistics,time
from pathlib import Path
D=Path('research-data/ai-sigma/164-native-route-choice')
p=Path('research-data/ai-sigma/160-pv-pipeline-bootstrap/fixtures.jsonl')
raw=p.read_bytes(); row=json.loads(raw.splitlines()[0])
def find(o):
 if isinstance(o,dict):
  for k,v in o.items():
   if isinstance(v,list) and len(v)==648 and all(isinstance(x,int) for x in v):return v
   r=find(v)
   if r is not None:return r
 elif isinstance(o,list):
  for v in o:
   r=find(v)
   if r is not None:return r
bits=find(row);assert bits is not None
req={'generation':1,'token':1,'features_bits':bits};reply={'generation':1,'token':1,'logits':[0.0]*136,'value':0.0,'synthetic':True}
t=[]
for i in range(9):
 start=time.perf_counter_ns()
 a=json.dumps(req,separators=(',',':')).encode()+b'\n';b=json.dumps(reply,separators=(',',':')).encode()+b'\n'
 assert json.loads(a)==req and json.loads(b)==reply
 if i:t.append((time.perf_counter_ns()-start)/1e6)
out={'fixture_source':str(p),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'request_bytes':len(a),'synthetic_reply_bytes':len(b),'warmup':1,'measured_codec_pairs':8,'codec_pair_ms':t,'median_codec_ms':statistics.median(t),'peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'NN':0,'IPC':0,'model_session':0,'actual_Rust_Node_ORT_route_unmeasured':True,'bits_roundtrip_equal':True}
(D/'codec-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
