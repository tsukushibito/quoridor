"""Post-result label-free exposure diagnostic; no mask/selection changes."""
from pathlib import Path
import sys,json,time,collections
R=Path.cwd();D=R/'research-data/ai-sigma/frame16-fit-gap-analysis/raw-cv-control';reg=json.loads((D/'preregister.json').read_text());sys.path.insert(0,str(R/'tools/nnue-training'))
from frame14_data import load_stage,signatures
rows,_=load_stage(reg['stage']);train=[r for r in rows if r['split']=='train'];counts=collections.Counter(r['group']for r in train);out=dict(rule='state OR history OR actual STM f32 QF1 input',label_free_only=True,mask_selection_changed=False,folds=[],planned_train_games=96,original_OOF_rowweight='1/(96*n_game)')
for k in range(5):
 refs={s for r in train if reg['game_folds'][r['group']]!=k for s in signatures(r)};held=[r for r in train if reg['game_folds'][r['group']]==k];shared=[];by=collections.defaultdict(lambda:dict(rows=0,shared_rows=0));types=collections.Counter()
 for r in held:
  hit=sorted(set(t for t,s in signatures(r)if (t,s)in refs));g=by[r['group']];g['rows']+=1;g['shared_rows']+=bool(hit)
  for t in hit:types[t]+=1
  if hit:shared.append(r)
 out['folds'].append(dict(fold=k,rows=len(held),games=len(by),shared_rows=len(shared),shared_original_OOF_mass=sum(1/(96*counts[r['group']])for r in shared),games_any_shared=sum(v['shared_rows']>0 for v in by.values()),games_zero_unexposed=sum(v['shared_rows']==v['rows']for v in by.values()),by_type=dict(types),pergame=dict(by)))
refs={s for r in train for s in signatures(r)};val=[r for r in rows if r['split']=='validation'];vc=collections.Counter(r['group']for r in val);sv=[r for r in val if any(s in refs for s in signatures(r))];out['fixed_validation']=dict(rows=len(val),games=len(vc),shared_rows=len(sv),shared_gameweight_mass=sum(1/(24*vc[r['group']])for r in sv));(D/'exposure.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in out.items()if k!='folds'}));print('OOFshared',sum(q['shared_rows']for q in out['folds']),sum(q['shared_original_OOF_mass']for q in out['folds']))
