import json,hashlib,datetime
from pathlib import Path
A=Path('.artifacts/ai-sigma/continuation-20261001/SIGMA-REMAINING-EVIDENCE-PLAN');final=json.loads((A/'evidence-choice-plan.json').read_text());node=json.loads((A/'node-static-check.json').read_text());original=json.loads((A/'evidence-choice-plan.json').read_text())
del original['m8_rejection_tradeoff'];del original['prospective_time_allocation']
for row in original['options']:
 if row['id']=='E3-clock-residual':row['smallest_experiment']=row['smallest_experiment'].replace('initial noCP at unchanged T500','noCP100 diagnostic(not rescue)')
b=(json.dumps(original,ensure_ascii=False,indent=2)+'\n').encode();assert hashlib.sha256(b).hexdigest()==node['plan_sha256'];(A/'tested-plan-revision1.json').write_bytes(b)
assert original['m8_hypothetical_only']==final['m8_hypothetical_only'];assert not final['m8_adopted'];assert final['new_match_preregister'] is None and final['new_engine_source_hash'] is None and not final['independent_acceptance']
s=datetime.datetime.fromisoformat('2026-10-01T22:30:00+00:00');windows=[20,35,25];ends=[]
for w in windows:s+=datetime.timedelta(minutes=w);ends.append(s.isoformat())
assert ends==['2026-10-01T22:50:00+00:00','2026-10-01T23:25:00+00:00','2026-10-01T23:50:00+00:00'];assert sum(windows)==80
assert (datetime.datetime.fromisoformat('2026-10-02T00:50:00+00:00')-s).total_seconds()==3600
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tested_revision_preserved_sha256':hashlib.sha256(b).hexdigest(),'final_plan_sha256':hashlib.sha256((A/'evidence-choice-plan.json').read_bytes()).hexdigest(),'original_final_arithmetic_inputs_identical':True,'new_prospective_path_minutes':80,'new_prospective_ends':ends,'prospective_heavy_stop_reserve_s':3600,'static_assertions_passed':True,'self_acceptance_issued':False,'actual_go':False,'new_PRNG_draw':False,'source_hash_placeholder':None,'m8_preregister_created':False,'NN':0,'engine':0,'games':0,'holdout_sends':0}
(A/'final-binding-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
