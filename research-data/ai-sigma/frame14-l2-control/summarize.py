"""Saved train/validation curve arithmetic only; never accesses any test."""
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path('tools/nnue-training').resolve()))
from test_contrast import interval

D=Path('research-data/ai-sigma/frame14-l2-control')
reg=json.loads((D/'preregister.json').read_text())
paths={'WD0':Path(reg['reuse_baseline']),'L2.01':D/'runs/frame14-l2-r1'}
hist={name:[json.loads(l) for l in (p/'history.jsonl').read_text().splitlines()] for name,p in paths.items()}
summary={};rows=[]
for name,h in hist.items():
    assert len(h)==21
    summary[name]={'before':h[0],'last':h[-1], 'best_positive_step':min((r['validation']['target_game_equal_mse'],r['step']) for r in h if r['step']>0)}
    for r in h:
        for split in ['train','validation']:
            rows.append({'condition':name,'step':r['step'],'train_samples':r['train_samples_seen'],
                         'epoch_equivalent':r['train_epochs_equivalent'],'split':split,**r[split]})
paired={}
for target in ['rootmean','z']:
    a={g:r[target+'_mse'] for g,r in hist['L2.01'][-1]['validation_games'].items()}
    b={g:r[target+'_mse'] for g,r in hist['WD0'][-1]['validation_games'].items()}
    paired[target]=interval(a,b)
result={'comparison':summary,'fixed_LAST_validation_L2_minus_WD0':paired,
        'interval_kind':'post-result exploratory paired24validation games; not the preregistered gate; no threshold adjustment',
        'test_read':False,'new_NN':0}
(D/'saved-curve-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
with (D/'curves/all-metrics.csv').open('w') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print(json.dumps({'curve_rows':len(rows),'paired_validation':paired,'test_read':False,'NN':0}))
