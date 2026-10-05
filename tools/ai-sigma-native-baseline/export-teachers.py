"""Only saved opening-root PV/z rows. Variable completed amount, same160 feature/action vocabulary."""
import sys,json,struct,hashlib,math,importlib.util
from pathlib import Path
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/165-native-baseline';A=R/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE'
spec=importlib.util.spec_from_file_location('readonly160',R/'tools/ai-sigma-pv-pipeline-bootstrap/bootstrap.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
fixed=json.loads((D/'stageB-inputs.json').read_text());rows=[];missing=[]
for game in fixed['games']:
 p=A/'runs'/('native165-pair'+str(game['pair']).zfill(2)+'-r1')/'result.json'
 if not p.exists():missing.append({'game':game['game_id'],'reason':'missing_result'});continue
 raw=p.read_bytes();g=next(x for x in json.loads(raw)['games'] if x['game_id']==game['game_id']);fr=g.get('firstRoot');f=next(x['fixture'] for x in fixed['rows'] if x['fixture'] and x['fixture']['id']==game['fixture_id'])
 if not g.get('pure_terminal_quality') or not fr or not fr.get('publicCP') or not fr.get('NN_bits'):missing.append({'game':game['game_id'],'reason':'outcome_or_root_missing'});continue
 cp=fr['publicCP']['cp'];edges=[[a,int(n)] for a,prior,n,value in cp['root_edges']];total=sum(n for a,n in edges)
 if total==0:missing.append({'game':game['game_id'],'reason':'zero_visits'});continue
 legal=f['root_state']['legal'];side=fr['side']-1;assert fr['key']==f['root_state']['key'];assert fr['features_bits']==f['root_state']['features_bits'];assert total==cp['root_visits']-1
 mp=b.mapping(fr['key'],side,legal);pi=[0.]*136
 for a,n in edges:assert a in mp and n>=0;pi[mp[a]]=n/total
 value=struct.unpack('<f',struct.pack('<I',fr['NN_bits'][136]))[0];z=0 if g['winner']==0 else 1 if g['winner']==fr['side'] else -1;sign=1 if side==0 else -1
 state={'key':fr['key'],'history':f['root_state']['history'],'side':side,'ply':f['target_ply'],'prefix':f['legal_prefix'],'walls_remaining':f['walls']}
 row={'schema':'pv-diagnostic-native-game-v2','fixture':f['id'],'engine':fr['engine'],'state':state,'features_bits':fr['features_bits'],'legal_actions':legal,'mapping136':[[a,mp[a]] for a in sorted(mp)],'edge_visits':edges,'pi136':pi,'teacher':{'K_requested':1000000,'completed_rootN':cp['root_visits'],'rootN':cp['root_visits'],'edge_sum':total,'root_nn_stm':value,'rootmean_stm':cp['root_mean'],'root_valueSum':cp['root_valueSum'],'root_nn_p1':sign*value,'rootmean_p1':sign*cp['root_mean'],'game_z':z,'game_z_p1':sign*z,'leaf_nn':None,'leaf_nn_missing':'not captured; no rootmean/rawrootNN relabeling','actual_nn_adopted':cp['nn_calls'],'actual_nn_started':fr['NN_calls'],'clock_ms':500,'cutoff_ms':402,'public_ms':411},'source':{'issue':'quoridor-4lc.165','game':game['game_id'],'pair':game['pair'],'raw':str(p.relative_to(R)),'raw_SHA256':hashlib.sha256(raw).hexdigest(),'lineage_master':91031,'model_SHA256':'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d','backend':'nativePythonORT1.30CPU1thread','formal_holdout':False,'diagnostic_only':True,'mapping_vocabulary_readonly160_SHA256':hashlib.sha256((R/'tools/ai-sigma-pv-pipeline-bootstrap/bootstrap.py').read_bytes()).hexdigest()}}
 row['group']=b.group(row);rows.append(row)
validation=min((x['group'] for x in rows),default=None)
for row in rows:row['split']='validation' if row['group']==validation else 'train'
for row in rows:
 st=row['state'];t=row['teacher'];ff=b.floats(row['features_bits']);assert len(ff)==648 and all(math.isfinite(x) for x in ff);assert len(st['prefix'])==st['ply'];assert len(row['pi136'])==136 and abs(sum(row['pi136'])-1)<1e-12;assert t['game_z'] in [-1,0,1];assert -1<=t['root_nn_stm']<=1 and -1<=t['rootmean_stm']<=1;assert abs(t['rootmean_stm']-t['root_valueSum']/t['rootN'])<1e-12;assert t['edge_sum']==t['rootN']-1
 for c,p in [(4,st['side']),(5,st['side']^1)]:assert all(abs(x-st['walls_remaining'][p]/10)<1e-6 for x in ff[c*81:(c+1)*81])
for group in {x['group'] for x in rows}:assert len({x['split'] for x in rows if x['group']==group})==1
(D/'opening-teachers.jsonl').write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows))
summary={'planned_opening_rows':16,'valid_rows':len(rows),'missing':missing,'groups':len({x['group'] for x in rows}),'train':sum(x['split']=='train' for x in rows),'validation':sum(x['split']=='validation' for x in rows),'shared160schema_not_overwritten':True,'variable_completed_amount_and_game_outcome_extension':True,'NN':0,'new_learning':0,'diagnostic_holdout_not_formal':True,'full_permove_dataset_not_exported':True}
(D/'opening-teacher-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
