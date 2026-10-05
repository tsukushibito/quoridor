"""Additional-seed NN0 preservation only, no model/Torch."""
from pathlib import Path
import json,csv,gzip,hashlib,tarfile
D=Path('research-data/ai-sigma/frame15-distance-update-control/seed19080312');O=D/'runs/frame15-distance-update-control-seed19080312-r1';M=Path('models/experiments/nnue/frame15-distance-update-control-seed19080312-r1')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=json.loads((D/'result.json').read_text());h=r['curves'];x=[q['step']for q in h];f,a=plt.subplots(1,2,figsize=(10,4))
a[0].plot(x,[q['raw_valgameMSE']for q in h],label='seed19080312 raw /209',marker='o');a[0].plot(x,[q['normalized_valgameMSE']for q in h],label='same function standardized /213 add1',marker='o');a[0].axhline(r['distance'],label='distance',ls='--',color='gray');a[0].axhline(r['constant'],label='constant',ls=':',color='gray');a[0].set_ylabel('Validation game-equal MSE')
a[1].plot(x,[q['train_gameMSE']for q in h],label='standardized train',marker='o');a[1].plot(x,[q['validation_z_gameMSE']for q in h],label='validation z',marker='o')
for ax in a:ax.set_xlabel('Fixed Adam steps');ax.legend(fontsize=8);ax.grid(alpha=.2)
f.suptitle('Additional joint seed / reused validation / no attenuation');f.tight_layout();f.savefig(D/'learning-curves.png',dpi=130);f.savefig(D/'learning-curves.svg');plt.close(f)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();files=list(M.glob('*.pt'));assert len(files)==3;members={str(p):dict(SHA=sha(p),B=p.stat().st_size)for p in files}
with tarfile.open(D/'weights.tar.gz','w:gz')as t:
 for p in files:t.add(p,arcname=str(p),recursive=False)
with tarfile.open(D/'weights.tar.gz','r:gz')as t:
 for m in t.getmembers():assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==members[m.name]['SHA']
(D/'weights-manifest.json').write_text(json.dumps(dict(archive=str(D/'weights.tar.gz'),SHA=sha(D/'weights.tar.gz'),members=members,restore_PASS=True,raw_and_archive_both_retained=True),indent=2)+'\n')
w=[json.loads(l)for l in gzip.open(O/'witness.jsonl.gz','rt')];obs=json.loads((O/'observer.json').read_text());old=Path('research-data/ai-sigma/frame15-learning-diagnostic/runs/frame15-learning-diagnostic-lr1e-4-seed19080312-r1');ow=[json.loads(l)for l in gzip.open(old/'witness.jsonl.gz','rt')];assert all(q['IDs']==ow[0]['IDs']for q in w)
updates=[dict(step=q['step'],**q['distance_coordinate_update'],fixed_witness_RMS_change=next(z for z in w if z['step']==q['step'])['prediction_step0_RMS_change'],raw_witness_RMS_change=next(z for z in ow if z['step']==q['step'])['prediction_step0_RMS_change'])for q in obs['observations']];(D/'coordinate-update-summary.json').write_text(json.dumps(dict(updates=updates,same_fixed12train=True,extra_forward_backward=0,attenuation_hook=False),indent=2)+'\n')
print(json.dumps(dict(weights=3,NN=0,curvepoints=4)))
