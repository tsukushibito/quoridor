"""NN0 bind fixed200 candidate and stopped source. No tensor import or forward."""
from pathlib import Path
import datetime,hashlib,json,math,time
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/frame14-distance-test';P=D.parent/'frame14-distance-residual';t=time.monotonic();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gate_path=P/'gate-result.json';g=json.loads(gate_path.read_text());assert g['issue']=='quoridor-4lc.200'
threshold=g['fixed_thresholds'];assert threshold['constant_gameMSE']==.6787804677332444 and threshold['random_QF1_gameMSE']==.6901755738627967 and threshold['margin']==.0001 and threshold['step0_allowed'] is True
score=g['candidate_validation_gameMSE'];assert math.isfinite(score)
settings_path=Path(g['evaluator_settings']);assert sha(settings_path)==g['evaluator_settings_SHA'];settings=json.loads(settings_path.read_text())
stop_path=Path(g['training_stop_path']);assert sha(stop_path)==g['training_stop_SHA'];stop=json.loads(stop_path.read_text());r=stop['science_job']
assert stop['scientific_source_stopped'] is True and r['exit']==0 and r['child_waited'] and not r['remaining'] and r['current_exact_identity_absent']
proc=Path('/proc')/str(r['identity']['pid'])/'stat'
try:tick=proc.read_text().rsplit(')',1)[1].split()[19]
except FileNotFoundError:tick=None
assert tick!=str(r['identity']['tick'])
parity_path=P/'initial-parity.json';parity=json.loads(parity_path.read_text());assert parity['pass'] and parity['rows']==5901 and parity['max_residual_abs']==0 and parity['atol']==1e-6 and parity['rtol']==1e-6
conditions={'below_constant':score<=threshold['constant_gameMSE']-.0001,'below_random_QF1':score<=threshold['random_QF1_gameMSE']-.0001,'finite_input_coefficient_schema':bool(parity['pass']),'science_child_stopped':True};assert conditions==g['conditions'];passed=all(conditions.values());assert (g['status']=='GATE_MET')==passed and g['new_test_generation_fixed_gate_authorized']==passed
assert settings['coefficients']==g['coefficients'] and settings['coefficient_fit_SHA']==g['coefficient_fit_SHA'] and settings['best_validation_gameMSE']==score
bindings={}
def bind(p,h):
 assert sha(p)==h,('BINDING_CHANGED',str(p));bindings[str(Path(p).resolve())]=h
bind(settings_path,g['evaluator_settings_SHA']);bind(stop_path,g['training_stop_SHA']);bindings[str(parity_path.resolve())]=sha(parity_path)
for p,h in g['private_sources'].items():assert stop['source_frozen'][p]==h;bind(ROOT/p,h)
reg=json.loads((P/'preregister.json').read_text());bind(ROOT/reg['fit_source'],g['coefficient_fit_SHA']);assert reg['coefficients']==g['coefficients'];bind(settings['config'],settings['config_SHA'])
for cp in settings['checkpoints'].values():bind(cp['path'],cp['checkpoint_SHA'])
assert g['candidate']['checkpoint_SHA']==settings['checkpoints']['best']['checkpoint_SHA']
bind(ROOT/'research-data/ai-sigma/frame14-teachers/final-qf1-v2/fixed-exposure-mask.json',g['mask_SHA'])
(D/'200-gate-result-snapshot.json').write_bytes(gate_path.read_bytes());a={'issue':'quoridor-4lc.201','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_path':str(gate_path),'gate_SHA256':sha(gate_path),'physical_handoff_stopped':True,'passed':passed,'conditions':conditions,'candidate_step':g['candidate_step'],'residual_benefit_validation':g['residual_benefit_validation'],'input_bindings_SHA256':bindings,'tensor_load_forward':0,'wall_s':time.monotonic()-t};(D/'gate-admission.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'passed':passed,'candidate_step':g['candidate_step'],'gateSHA':a['gate_SHA256'],'bound_files':len(bindings),'NN_GPU':0,'wall_s':a['wall_s']}))
