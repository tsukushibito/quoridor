"""Arithmetic summaries of saved curves only; no model imports/forward."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

D=Path('research-data/ai-sigma/frame14-learning')
stages={n:json.loads((D/f'stages/train{n}.stage.json').read_text()) for n in (24,48,96)}
groups={n:set(s['train_groups']) for n,s in stages.items()}
cohorts={'first24':groups[24],'added25_48':groups[48]-groups[24],'added49_96':groups[96]-groups[48]}
curves=[];cohort_results={};weights=[]
for n in (24,48,96):
    run=D/f'runs/frame14-train{n}-r1'
    history=[json.loads(l) for l in (run/'history.jsonl').read_text().splitlines()]
    cohort_results[str(n)]={}
    for endpoint,r in [('before',history[0]),('last',history[-1])]:
        cohort_results[str(n)][endpoint]={}
        for name,gs in cohorts.items():
            a=[r['train_games'][g] for g in sorted(gs) if g in r['train_games']]
            if not a:continue
            total=sum(x['rows'] for x in a)
            entry={'games':len(a),'rows':total}
            for k in ['rootmean','z']:
                entry[k+'_row_mse']=sum(x[k+'_mse']*x[k+'_rows'] for x in a)/sum(x[k+'_rows'] for x in a)
                entry[k+'_game_mse']=sum(x[k+'_game_equal_mse'] for x in a)/len(a)
            entry['z_sign_row_accuracy']=sum(x['z_sign_accuracy']*x['z_sign_rows'] for x in a)/sum(x['z_sign_rows'] for x in a)
            entry['saturation_row_fraction']=sum(x['saturation_fraction']*x['rows'] for x in a)/total
            cohort_results[str(n)][endpoint][name]=entry
    for r in history:
        for split in ['train','validation']:
            curves.append({'stage':n,'step':r['step'],'train_samples_seen':r['train_samples_seen'],
                           'epochs_equivalent':r['train_epochs_equivalent'],'elapsed_s':r['elapsed_s'],
                           'split':split,**r[split]})
    for p in sorted(Path(f'models/experiments/nnue/frame14-train{n}-r1').glob('*.pt')):
        weights.append({'path':str(p.resolve()),'B':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(D/'train-prefix-cohorts.json').write_text(json.dumps(cohort_results,indent=2)+'\n')
(D/'weights-manifest.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                                'weights':weights,'weightbyte_hash_only':True,'new_forward':0},indent=2)+'\n')
with (D/'curves/full-metrics.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(curves[0]));writer.writeheader();writer.writerows(curves)
print(json.dumps({'all3histories_arithmetic':True,'curve_rows':len(curves),'cohort_groups_complete':True,
                  'weights_files':len(weights),'weights_B':sum(p['B'] for p in weights),'NN':0}))
