"""NN0 mapping/shape and framing checks without importing torch or model."""
import ast, hashlib, json, struct
from pathlib import Path
D=Path('research-data/ai-sigma/174-gpu-inference');T=Path('tools/ai-sigma-gpu-inference')
for p in T.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
g=json.loads(Path('research-data/ai-sigma/171-gpu-route-choice/graph-evidence.json').read_text())
w={x['name']:x['shape'] for x in g['initializers']};n={x['name']:x for x in g['nodes']}
assert len(w)==83 and len(n)==179
names=['/conv/Conv','/policy_h_conv/Conv','/policy_v_conv/Conv','/value_conv/Conv']+[f'/residuals/residuals.{i}/conv{j}/Conv' for i in range(10) for j in (1,2)]
for name in names:
 x=n[name];assert x['op']=='Conv' and x['inputs'][1] in w
 if len(x['inputs'])==3:assert w[x['inputs'][2]]==[w[x['inputs'][1]][0]]
assert w['onnx::Conv_439']==[128,8,3,3] and w['policy_pawn_fc1.weight']==[64,384]
for i in (2,5,8):
 for kind,c in [('reg',96),('pool',32)]:
  x=n[f'/residuals/residuals.{i}/bn1_{kind}/BatchNormalization'];assert x['attrs']['training_mode']==0
  assert all(w[y]==[c] for y in x['inputs'][1:])
 r=n[f'/residuals/residuals.{i}/conv2/Conv'];assert w[r['inputs'][1]]==[128,96,3,3]
inputs=json.loads((D/'inputs.json').read_text())
assert len(inputs['inputs'])==5
for row in inputs['inputs']:
 bits=row['features_bits'];assert len(bits)==648 and all(type(x)==int and 0<=x<2**32 for x in bits)
 assert all((x&0x7f800000)!=0x7f800000 for x in bits)
 assert json.loads(json.dumps(bits))==bits
# Invalid schema must be rejected before NN.
rejected=0
for bad in ([0]*647,[0x7f800000]*648):
 try:assert len(bad)==648 and all((x&0x7f800000)!=0x7f800000 for x in bad)
 except AssertionError:rejected+=1
assert rejected==2
out={'NN_CUDA_session_forward':0,'all5_shape_finite_bits':True,'all24Conv_6BN_mapping_shapes':True,'invalid_length_and_nonfinite_rejected':rejected,'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in T.glob('*.py')}}
(D/'NN0-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
