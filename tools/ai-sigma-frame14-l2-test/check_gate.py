"""NN0 fixed-gate arithmetic and stopped physical receipt; never launches science."""
from pathlib import Path
import datetime,hashlib,json,math,time
D=Path(__file__).resolve().parents[2]/'research-data/ai-sigma/frame14-l2-test'
P=D.parent/'frame14-l2-control';t=time.monotonic();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
gate_path=P/'gate-result.json';g=json.loads(gate_path.read_text());receipt_path=P/'jobs/l2-train-r1/process.json';r=json.loads(receipt_path.read_text())
assert g['issue']=='quoridor-4lc.197' and g['margin_fixed']==.0001
assert r['exit']==0 and r['child_waited'] and not r['remaining'] and r['current_exact_identity_absent']
identity=r['identity'];proc=Path('/proc')/str(identity['pid'])/'stat'
try:currenttick=proc.read_text().rsplit(')',1)[1].split()[19]
except FileNotFoundError:currenttick=None
assert currenttick!=str(identity['tick']),'197_IDENTITY_STILL_LIVE'
score=g['best_validation_gameMSE'];assert all(math.isfinite(g[x]) for x in ['best_validation_gameMSE','WD0_best_gameMSE','trainconstant_validation_gameMSE'])
conditions={'beststep_positive':g['best_step']>0,'different_weights':g['checkpoints']['best']['weight_SHA']!=g['initial_SHA'],'below_WD0_best_by_margin':score<=g['WD0_best_gameMSE']-.0001,'below_trainconstant_by_margin':score<=g['trainconstant_validation_gameMSE']-.0001}
assert conditions==g['conditions'];passed=all(conditions.values());assert (g['status']=='GATE_MET')==passed and g['newtest_generation_authorized_by_fixed_gate']==passed
bindings={}
for checkpoint in g['checkpoints'].values():
 p=Path(checkpoint['path']);assert sha(p)==checkpoint['checkpoint_SHA'];bindings[str(p)]={'SHA256':sha(p),'bytes':p.stat().st_size}
config=Path(g['config_path']);assert sha(config)==g['config_SHA'];bindings[str(config)]={'SHA256':sha(config)}
(D/'197-gate-result-snapshot.json').write_bytes(gate_path.read_bytes())
a={'issue':'quoridor-4lc.198','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_path':str(gate_path),'gate_SHA256':sha(gate_path),'receipt_path':str(receipt_path),'receipt_SHA256':sha(receipt_path),'physical_handoff_stopped':True,'conditions':conditions,'passed':passed,'input_binding':bindings,'NN_GPU_tensor_load':0,'wall_s':time.monotonic()-t};(D/'gate-admission.json').write_text(json.dumps(a,indent=2)+'\n')
slots=json.loads((D/'all24-slot-status.json').read_text());assert len(slots)==24
if not passed:
 for s in slots:s.update(status='NOT_STARTED',reason='GATE_NOT_MET',Rpolicy=0,Rz=0,Rjoint=0)
 (D/'all24-slot-status.json').write_text(json.dumps(slots,indent=2)+'\n')
print(json.dumps({'passed':passed,'conditions':conditions,'wall_s':a['wall_s'],'NN_GPU':0,'all24_status':'NOT_STARTED GATE_NOT_MET' if not passed else 'NOT_STARTED gatepassed currentadmission pending'}))
