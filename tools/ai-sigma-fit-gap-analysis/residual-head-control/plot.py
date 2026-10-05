from pathlib import Path
import json,gzip
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('research-data/ai-sigma/frame16-fit-gap-analysis/residual-head-control');a=json.loads(gzip.decompress((D/'residual-analysis.json.gz').read_bytes()));names=['D','distance_recalibration','standard400','ridge'];fig,ax=plt.subplots(figsize=(7,3.8))
for i,split in enumerate(['train','validation']):
 ms=a['splits'][split];v=[ms['ridge']['distance_gameMSE']]+[ms[n]['NN_gameMSE']for n in names[1:]];ax.bar([j+(-.19 if i==0 else .19)for j in range(4)],v,width=.38,label=split)
ax.set_xticks(range(4),['Distance','Distance recalibration','Standard 400','Frozen hidden ridge'],rotation=12);ax.set_ylabel('Game-equal rootmean MSE');ax.legend();ax.set_title('Fixed train-only ridge: fit improves, validation remains above distance');fig.tight_layout();fig.savefig(D/'comparison.png',dpi=140);fig.savefig(D/'comparison.svg');plt.close(fig)
