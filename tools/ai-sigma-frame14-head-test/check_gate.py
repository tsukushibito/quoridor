"""NN0 physical binding of the unique head-only gate; no tensor load/forward."""
from pathlib import Path
import datetime,hashlib,json,math,time
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/frame14-head-test';P=D.parent/'frame14-head-control';t=time.monotonic();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gate_path=P/'gate-result.json';g=json.loads(gate_path.read_text());assert g['issue']=='quoridor-4lc.204'
assert g['baseline_validation_gameMSE']==.48514681311997876 and g['margin']==.0001
bindings={}
def bind(p,h):
 p=Path(p);assert sha(p)==h,('BINDING_CHANGED',str(p));bindings[str(p.resolve())]=h
settings_path=Path(g['evaluator_settings']);bind(settings_path,g['settings_SHA']);settings=json.loads(settings_path.read_text())
stop_path=Path(g['stop']);bind(stop_path,g['stop_SHA']);stop=json.loads(stop_path.read_text());r=stop['scientific_child_stop']
assert stop['scientific_source_stopped'] is True and r['exit']==0 and r['child_waited'] and not r['remaining'] and r['current_exact_identity_absent']
try:tick=(Path('/proc')/str(r['identity']['pid'])/'stat').read_text().rsplit(')',1)[1].split()[19]
except FileNotFoundError:tick=None
assert tick!=str(r['identity']['tick'])
schema_path=P/'finite-schema.json';bind(schema_path,g['finite_schema_SHA']);s=json.loads(schema_path.read_text());assert s['pass'] and s['initial_full_tensor_exact'] and s['optimizer_head_only'] and s['trainable_names']==['out.weight','out.bias'] and s['trainable_parameters']==33
f=s['frozen_tensor_exact'];assert f['initial']==f['best']==f['last'] and set(f['initial'])=={'ft.weight','ft.bias','h.weight','h.bias','distance_a','distance_b'}
assert s['initial_distance_parity']['pass'] and s['old_test_read'] is False
score=g['best_validation_gameMSE'];assert math.isfinite(score)
assert settings['best_validation_gameMSE']==score and settings['best_step']==g['best_step']
assert settings['coefficients']==g['coefficients']=={'a':.06294242415104226,'b':8.276425107422213}
assert settings['coefficient_fit_SHA']==g['coefficient_fit_SHA']=='77ce9e79495038b25a4f4a9ffd95dc9f66700aff2c1f96cf08b65fff3c79733c'
assert g['candidate']==settings['checkpoints']['best'] and g['initial']==settings['checkpoints']['initial']
for cp in settings['checkpoints'].values():bind(cp['path'],cp['checkpoint_SHA'])
for p,h in g['source_SHA'].items():assert stop['scientific_source_SHA'][p]==h;bind(ROOT/p,h)
bind(settings['config'],settings['config_SHA']);bind(ROOT/'tools/ai-sigma-qf1-distance-residual/residual_model.py',settings['forward_source_SHA'])
conditions={'beststep_positive_and_weight_changed':g['best_step']>0 and g['candidate']['weight_SHA']!=g['initial']['weight_SHA'],'below_distanceinitial_by_margin':score<.48514681311997876-.0001,'finite_coeff_input_lowerlayer_schema':True,'source_science_child_stop_currentexact_absent':True}
assert conditions==g['conditions'];passed=all(conditions.values());assert (g['status']=='GATE_MET')==passed and g['generation_authorized']==passed
(D/'204-gate-result-snapshot.json').write_bytes(gate_path.read_bytes());a={'issue':'quoridor-4lc.205','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_path':str(gate_path),'gate_SHA256':sha(gate_path),'physical_handoff_stopped':True,'passed':passed,'conditions':conditions,'candidate_step':g['best_step'],'input_bindings_SHA256':bindings,'tensor_load_forward':0,'wall_s':time.monotonic()-t};(D/'gate-admission.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'passed':passed,'candidate_step':g['best_step'],'gateSHA':a['gate_SHA256'],'bound_files':len(bindings),'NN_GPU':0,'wall_s':a['wall_s']}))
