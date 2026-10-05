"""NN0 curves, checkpoint archive, and typed update summaries; no Torch/model."""
from pathlib import Path
import csv,datetime,gzip,hashlib,json,tarfile
R=Path.cwd();D=R/'research-data/ai-sigma/frame15-input-scale-control';O=D/'runs/frame15-input-scale-control-r1';M=R/'models/experiments/nnue/frame15-input-scale-control-r1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with (D/'curves.csv').open()as f:rows=list(csv.DictReader(f))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
x=[int(r['step'])for r in rows];fig,axes=plt.subplots(1,2,figsize=(10,4))
axes[0].plot(x,[float(r['old_validation_gameMSE'])for r in rows],label='raw distance /209',marker='o');axes[0].plot(x,[float(r['standardized_validation_gameMSE'])for r in rows],label='standardized distance /211',marker='o');axes[0].axhline(.48514681311997876,color='gray',ls='--',label='distance baseline');axes[0].axhline(.6787804677332444,color='gray',ls=':',label='train constant');axes[0].set_ylabel('Validation game-equal rootmean MSE');axes[0].legend(fontsize=8)
axes[1].plot(x,[float(r['train_gameMSE'])for r in rows],label='standardized train',marker='o');axes[1].plot(x,[float(r['val_z_gameMSE'])for r in rows],label='validation z MSE',marker='o');axes[1].legend(fontsize=8)
for ax in axes:ax.set_xlabel('Adam step (fixed 10 points)');ax.grid(alpha=.2)
fig.suptitle('Single seed / reused validation; same initial function, different optimizer coordinates');fig.tight_layout();fig.savefig(D/'learning-curves.png',dpi=140);fig.savefig(D/'learning-curves.svg');plt.close(fig)
files=list(M.glob('*.pt'));assert len(files)==3;archive=D/'weights.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(R)),recursive=False)
members={str(p.relative_to(R)):{'SHA':sha(p),'B':p.stat().st_size}for p in files}
with tarfile.open(archive,'r:gz')as tar:
 for p in tar.getmembers():assert hashlib.sha256(tar.extractfile(p).read()).hexdigest()==members[p.name]['SHA']
(D/'weights-manifest.json').write_text(json.dumps({'archive':str(archive.relative_to(R)),'SHA':sha(archive),'members':members,'restore_PASS':True,'raw_models_and_archive_both_retained':True},indent=2)+'\n')
w=[json.loads(x)for x in gzip.decompress((O/'witness.jsonl.gz').read_bytes()).splitlines()];old=R/'research-data/ai-sigma/frame15-learning-diagnostic/runs/frame15-learning-diagnostic-lr1e-4-r1';ow=[json.loads(x)for x in gzip.decompress((old/'witness.jsonl.gz').read_bytes()).splitlines()];assert all(r['IDs']==ow[0]['IDs']for r in w)
obs=json.loads((O/'observer.json').read_text());updates=[{'step':r['step'],**r['distance_coordinate_update'],'witness_step0_RMS_change':next(q for q in w if q['step']==r['step'])['prediction_step0_RMS_change'],'old_witness_step0_RMS_change':next(q for q in ow if q['step']==r['step'])['prediction_step0_RMS_change']}for r in obs['observations']];(D/'raw-coordinate-update-summary.json').write_text(json.dumps({'rule':'DeltaWd_raw=DeltaWdprime/sigma; dbraw=dbprime-sum(dwprime*mu/sigma)','updates':updates,'same12train_witnessIDs':True,'extra_forward_backward':0,'sigma_small_effect':'same Adam LR in standardized parameters implies different, larger raw distance-column updates plus centering/bias coupling; no information/capacity added'},indent=2)+'\n')
refs={str(p.relative_to(R)):sha(p)for p in [old/'history.jsonl.gz',old/'observer.json',old/'witness.jsonl.gz',R/'research-data/ai-sigma/frame15-learning-diagnostic/final-science-stop.json']};(D/'old209-readonly-reference-SHA.json').write_text(json.dumps(refs,indent=2)+'\n')
print(json.dumps({'archive_members':len(files),'extra_NN':0,'curves':10,'witness_same12':True,'update200':next(r for r in updates if r['step']==200)}))
