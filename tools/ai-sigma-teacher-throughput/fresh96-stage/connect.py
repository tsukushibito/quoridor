"""NN0 shared-canonical export/exposure diagnostic; no model, target-based mask or split selection."""
from pathlib import Path
import sys,json,gzip,hashlib,datetime,time
R=Path.cwd();O=R/'research-data/ai-sigma/frame16-teacher-throughput/fresh96-stage'
sys.path.insert(0,str(R/'tools/nnue-training'))
from frame14_data import signatures,feature_signature,read_rows,sha
st=time.monotonic();meta=read_rows(O/'metadata.jsonl.gz');spec=json.loads((O/'openings.json').read_text())['games'];seen=set();refs=[]
for p in [R/'research-data/ai-sigma/frame14-teachers/final-qf1-v2/all144-metadata.jsonl.gz',R/'research-data/ai-sigma/frame14-distance-test/canonical-export-r1/test-metadata.jsonl.gz']:
 rr=read_rows(p)
 for x in rr:
  assert not set(x)&{'rootmean','rootNN','z','z_stm','winner','loss'}
  seen.update(signatures(x))
 refs.append(dict(path=str(p),SHA=sha(p),rows=len(rr),labels_read=False))
games={g['game_id']:dict(game_id=g['game_id'],family=g['family'],rows=0,unshared_rows=0,shared_rows=0,state=0,history=0,QF1=0)for g in spec}
rows=[];types={'state':0,'history':0,'QF1':0};newseen=set();withinshared=0
for x in meta:
 assert not set(x)&{'rootmean','rootNN','z','z_stm','winner','loss'}
 ss=signatures(x);exp=sorted(k for k,v in ss if(k,v)in seen);withinshared+=any(s in newseen for s in ss);newseen.update(ss);x['QF1_input_sha256']=feature_signature(x);x['exposure_to_old_label_free_reference']=exp
 g=games[x['game_id']];g['rows']+=1;g['shared_rows']+=bool(exp);g['unshared_rows']+=not exp
 for k in exp:types[k]+=1;g[k]+=1
 rows.append(x)
p=O/'canonical-metadata.jsonl.gz';assert not p.exists();p.write_bytes(gzip.compress(('\n'.join(json.dumps(x,separators=(',',':'))for x in rows)+'\n').encode(),mtime=0))
out=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_games=96,actual_metadata_games=sum(g['rows']>0 for g in games.values()),rows=len(rows),old_reference_exposure_OR_rows=sum(g['shared_rows']for g in games.values()),old_reference_unshared_rows=sum(g['unshared_rows']for g in games.values()),types=types,games=list(games.values()),zero_row_games=[g['game_id']for g in games.values()if not g['rows']],zero_unshared_games=[g['game_id']for g in games.values()if not g['unshared_rows']],within_new_prior_row_any_signature_shared=withinshared,refs=refs,canonical_api_SHA=sha(R/'tools/nnue-training/frame14_data.py'),target_or_loss_used=False,eligibility_or_training_split_changed=False,not_IID_or_all_state_independent=True,wall_s=time.monotonic()-st)
(O/'exposure-summary.json').write_text(json.dumps(out,indent=2)+'\n')
m=dict(kind='fresh96-teacher-dataset-candidate',metadata=str(p),metadata_sha256=sha(p),labels=str(O/'labels.jsonl.gz'),labels_sha256=sha(O/'labels.jsonl.gz'),planned_openings=str(O/'openings.json'),planned_openings_sha256=sha(O/'openings.json'),planned_games=96,familygroups=96,role='evaluation-only productioncandidate; not independent test; no trainval assignment',auto_training_mix=False,reference_exposure=str(O/'exposure-summary.json'),canonical_version='QF1-f32-STM-v1',labels_are_new_dataset_only=True)
(O/'dataset-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['planned_games','actual_metadata_games','rows','old_reference_exposure_OR_rows','old_reference_unshared_rows','types','wall_s']}))
