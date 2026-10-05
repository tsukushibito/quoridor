from pathlib import Path
import gzip,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path('research-data/ai-sigma/frame16-fit-gap-analysis');D=B/'raw-linear-control';a=json.loads(gzip.decompress((D/'residual-analysis.json.gz').read_bytes()));p=json.loads(gzip.decompress((B/'residual-head-control/residual-analysis.json.gz').read_bytes()));fig,ax=plt.subplots(figsize=(7,3.6))
for i,split in enumerate(['train','validation']):
 q=a['splits'][split];q2=p['splits'][split];v=[q['raw_linear']['distance_gameMSE'],q['distance2_reference']['NN_gameMSE'],q2['ridge']['NN_gameMSE'],q['raw_linear']['NN_gameMSE']];ax.bar([j+(-.19 if i==0 else .19)for j in range(4)],v,.38,label=split)
ax.set_xticks(range(4),['Distance D','Distance2 ridge','Learned hidden ridge','Raw626 ridge'],rotation=10);ax.set_ylabel('Game-equal rootmean MSE');ax.set_title('Fixed residual probes: train fit and validation transfer differ');ax.legend();fig.tight_layout();fig.savefig(D/'comparison.png',dpi=140);fig.savefig(D/'comparison.svg');plt.close(fig)
