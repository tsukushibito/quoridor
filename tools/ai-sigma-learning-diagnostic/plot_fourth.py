"""Separate combined-four-condition figure from saved metrics only."""
"""Standalone figures from saved diagnostic metrics; no forward."""
import gzip
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D=Path('research-data/ai-sigma/frame15-learning-diagnostic')
fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
obs,ox=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
for path in sorted((D/'runs').iterdir()):
    rows=[json.loads(s)for s in gzip.decompress((path/'history.jsonl.gz').read_bytes()).splitlines()]
    witness=[json.loads(s)for s in gzip.decompress((path/'witness.jsonl.gz').read_bytes()).splitlines()]
    o=json.loads((path/'observer.json').read_text());name=o['condition'];steps=[r['step']for r in rows]
    tr=[r['train']['rootmean_game_equal_mse']for r in rows];va=[r['validation']['rootmean_game_equal_mse']for r in rows]
    axes[0].plot(steps,tr,marker='.',label=name);axes[1].plot(steps,va,marker='.',label=name)
    axes[2].plot(tr,va,marker='.',label=name)
    ox[0].plot(steps,[r['prediction_step0_RMS_change']for r in witness],marker='.',label=name)
    ox[1].plot([r['step']for r in o['observations']],[r['ft_active_columns']['update_to_weight_ratio']for r in o['observations']],marker='.',label=name)
    ox[2].plot(steps,[r['validation']['saturation_fraction']for r in rows],marker='.',label=name)
axes[1].axhline(.6787804677332444,color='gray',ls=':',label='train-only constant')
axes[1].axhline(.48514681311997876,color='black',ls='--',label='train-fit distance')
for i,title in enumerate(['Train game-equal rootmean MSE','Reused validation game-equal MSE','Optimization trajectory (same batches)']):
    axes[i].set_title(title);axes[i].set_ylabel('rootmean game-equal MSE');axes[i].grid(alpha=.25);axes[i].legend(fontsize='small')
    axes[i].set_xlabel('step (128 train samples/step)'if i<2 else'train game-equal MSE')
    if i<2:axes[i].set_xscale('symlog',linthresh=2)
for i,(title,label)in enumerate([('Fixed train witnesses, same eval forward','prediction RMS change from step0'),('Active sparse FT columns','update / active weight norm'),('Validation output saturation','fraction |value| >= 0.9')]):
    ox[i].set(title=title,xlabel='step',ylabel=label);ox[i].set_xscale('symlog',linthresh=2);ox[i].grid(alpha=.25);ox[i].legend(fontsize='small')
ox[1].set_yscale('log')
for figure,name in [(fig,'four-condition-learning-curves'),(obs,'four-condition-observer-curves')]:
    figure.savefig(D/(name+'.png'),dpi=140);figure.savefig(D/(name+'.svg'));plt.close(figure)
