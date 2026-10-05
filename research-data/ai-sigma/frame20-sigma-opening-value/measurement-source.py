import os, json, hashlib, subprocess, time, datetime, resource
from pathlib import Path
os.sched_setaffinity(0, {3})
R=Path('/workspaces/quoridor')
W=R/'.worktree/ai-sigma'
D=R/'research-data/ai-sigma/frame20-sigma-opening-value'
D.mkdir(parents=True,exist_ok=True)
manifest=W/'research-data/ai-sigma/frame20-distance-arena/openings8-v1.json'
model=W/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx'
assert hashlib.sha256(model.read_bytes()).hexdigest()=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'
code="""
const fs=require('fs'),assert=require('assert');
const {r}=require(process.argv[1]+'/tools/ai-sigma-native-baseline/reference.cjs').createReference();
const m=JSON.parse(fs.readFileSync(process.argv[2]));
console.log(JSON.stringify(m.openings.map(o=>{
 const s=r.fromPrefix(o.prefix);assert.equal(s._positionKey(),o.key);assert(!r.terminalResult(s));
 const recorded=JSON.parse(o.history);
 assert.equal(recorded[0],s._positionKey());assert.equal(recorded[1],s.position_history.get(s._positionKey()));
 const sort=x=>x.slice().sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
 assert.deepEqual(sort(Array.from(s.position_history)),sort(recorded[2]));
 return {id:o.id,ply:o.opening_ply,side:s.getCurrentPlayer(),key:o.key,history:o.history,prefix:o.prefix,features_bits:r.portState(s).features_bits};
})));
"""
t0=time.monotonic()
p=subprocess.run(['node','-e',code,str(W),str(manifest)],capture_output=True,text=True,timeout=5)
assert p.returncode==0,p.stderr
rows=json.loads(p.stdout)
assert len(rows)==2
import numpy as np
import onnxruntime as ort
opt=ort.SessionOptions();opt.intra_op_num_threads=opt.inter_op_num_threads=1
opt.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
s=ort.InferenceSession(str(model),sess_options=opt,providers=['CPUExecutionProvider'])
for row in rows:
 x=np.asarray(row['features_bits'],dtype=np.uint32).view(np.float32).reshape(1,8,9,9)
 assert np.isfinite(x).all()
 t=time.monotonic();out=s.run(None,{s.get_inputs()[0].name:x})
 v=next(a for a in out if a.size==1).reshape(-1)
 assert v.dtype==np.float32 and np.isfinite(v).all() and abs(float(v[0]))<=1
 row.update(value_stm=float(v[0]),infer_ms=(time.monotonic()-t)*1000)
result={'issue':'quoridor-4lc.255','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model_SHA256':hashlib.sha256(model.read_bytes()).hexdigest(),'opening_manifest_SHA256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'ORT':ort.__version__,'providers':s.get_providers(),'CPU':[3],'threads':1,'NN':2,'warmup':0,'search':0,'perspective':'side to move','rows':rows,'wall_s':time.monotonic()-t0,'peak_RSS_B':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'node_child_exit':p.returncode,'node_child_waited':True}
(D/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sum(f.stat().st_size for f in D.iterdir() if f.is_file())<65536
print(json.dumps({k:result[k] for k in ['NN','wall_s','peak_RSS_B','ORT','providers']}))
print(json.dumps([{k:r[k] for k in ['id','ply','side','value_stm','infer_ms']}for r in rows]))
