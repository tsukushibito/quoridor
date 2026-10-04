"""Owner-only dataset assembly. Test targets never enter training labels."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,subprocess
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning';OLD=R/'research-data/ai-sigma/frame16-teacher-throughput/fresh96-stage'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:[json.loads(l)for l in gzip.open(p,'rt')if l.strip()]
out=D/'dataset-v1';assert not out.exists();out.mkdir()
plan={'kind':'QF1-dynamic-plan','games':[],'stages':[192,576],'old96_alias_reason':'old evaluation-only candidate explicitly train in this new version; old IDs/groups/version untouched'}
paths=[OLD/'canonical-metadata.jsonl.gz'];labels=[dict(r,split='train')for r in read(OLD/'labels.jsonl.gz')]
oldmeta=read(paths[0]);counts=collections.Counter(r['game_id']for r in oldmeta)
for i,g in enumerate(json.loads((OLD/'openings.json').read_text())['games'],1):
 plan['games'].append(dict(game_id=g['game_id'],family=g['family'],split='train',source_split='evaluation',cohort='opening-'+str(g['target_ply']),expected_rows=counts[g['game_id']],train_slot=i))
counts=collections.Counter();testfiles=[];seen=set()
for O in sorted(list((D/'jobs').glob('*'))+list((D/'test-sealed/jobs').glob('*'))):
 meta=O/'metadata.jsonl.gz'
 if not meta.exists():continue
 process=json.loads((O/'process.json').read_text());assert process['all_child_waited']and process['current_exact_absent']
 rr=read(meta);assert not seen.intersection(r['id']for r in rr);seen.update(r['id']for r in rr)
 paths.append(meta);counts.update(r['game_id']for r in rr)
 if rr and rr[0]['split']=='test':testfiles.append(O/'labels.jsonl.gz')
 elif rr:labels.extend(read(O/'labels.jsonl.gz'))
for n in ['val96','test96','train01','train02','train03','train04','train05']:
 for g in json.loads((D/f'{n}-openings.json').read_text())['games']:
  row=dict(game_id=g['game_id'],family=g['family'],split=g['split'],cohort='opening-'+str(g['target_ply']),expected_rows=counts[g['game_id']])
  if g['split']=='train':row['train_slot']=g['train_slot']
  plan['games'].append(row)
training=out/'training-labels.jsonl.gz'
with gzip.open(training,'wt')as f:
 for r in labels:assert r['split']in ['train','validation'];f.write(json.dumps(r)+'\n')
sealed=D/'test-sealed/test-labels-combined-v1.jsonl.gz';assert not sealed.exists()
with gzip.open(sealed,'wb')as f:
 for p in testfiles:
  with gzip.open(p,'rb')as src:
   while b:=src.read(1024*1024):f.write(b)
plan['training_labels_advertised']={'path':str(training),'sha256':sha(training)}
plan['sealed_test_advertised']={'path':str(sealed),'sha256':sha(sealed)}
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
positive={s:sum(g['split']==s and g['expected_rows']>0 for g in plan['games'])for s in ['train','validation','test']}
small=sum(g['split']=='train'and g['train_slot']<=192 and g['expected_rows']>0 for g in plan['games'])
large=positive['train'];points=[0,1,2,5,10,20,50,100,200,400,800,1200,2000]
chosen=min(points,key=lambda x:(abs(x/large-400/small),x))if small and large else None
quantity={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'planned_new_games':672,'train_planned':576,'positive':positive,'small_positive':small,
 'branch':'full planned192/576 with effective G+ explicitly reported; if missing families, retained plannedzero rows with acquired effective maximum before curves',
 'holdout_complete':positive['validation']==96 and positive['test']==96,'all_slots':plan['games'],
 'secondary_nonselection':{'small_step':400,'large_step':chosen,'G_small':small,'G_large':large,'distance':abs(chosen/large-400/small)if chosen is not None else None,'rule':'minimum saved abs(step/Glarge-400/Gsmall); tie early; before curves'},
 'test_target_values_decoded':False}
(out/'quantity-freeze.json').write_text(json.dumps(quantity,indent=2)+'\n')
cmd=['/usr/bin/python3','-B',str(R/'tools/ai-sigma-frame18-learning/manifest_adapter.py'),'--plan',str(out/'plan.json'),'--out',str(out/'adapter')]
for p in paths:cmd.extend(['--metadata',str(p)])
subprocess.run(cmd,check=True)
print(json.dumps({'dataset':str(out),'positive':positive,'test_target_values_decoded':False,'NN':0}))
