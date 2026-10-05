"""Scientific figures from preserved scalar outputs; NN0."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path('research-data/ai-sigma/frame16-fit-gap-analysis');r=json.loads((D/'residual-analysis.json').read_text());names=['plain200','plain400','standard200','standard400'];f,a=plt.subplots(1,2,figsize=(12,4))
for j,split in enumerate(['train','validation']):
 values=[r['splits'][split][n]['NN_gameMSE']for n in names];a[0].bar([i+(j-.5)*.32 for i in range(4)],values,.32,label=split)
 a[0].axhline(r['splits'][split]['plain200']['distance_gameMSE'],label=split+' fixed distance',ls='--'if j==0 else':',color='gray')
a[0].set_xticks(range(4),names,rotation=15);a[0].set_ylabel('Game-equal rootmean MSE');a[0].legend(fontsize=8)
for i,split in enumerate(['train','validation']):
 x=r['splits'][split]['standard400'];a[1].bar(i-.2,x['displacement_MSE'],.2,label='E[r^2]'if i==0 else None);a[1].bar(i,-2*x['alignment_cross_E_eD_rNN'],.2,label='-2E[e r]'if i==0 else None);a[1].bar(i+.2,x['delta_NN_minus_D'],.2,label='NN minus D'if i==0 else None)
a[1].set_xticks(range(2),['train96','validation24']);a[1].axhline(0,color='gray',lw=.7);a[1].set_ylabel('standard400 signed game-equal contribution');a[1].legend(fontsize=8)
for ax in a:ax.grid(axis='y',alpha=.2)
f.suptitle('Matched train / reused validation: early fit gap, later transfer gap');f.tight_layout();f.savefig(D/'fit-gap.png',dpi=140);f.savefig(D/'fit-gap.svg');plt.close(f)
f,a=plt.subplots(1,3,figsize=(14,4))
for ax,dim in zip(a,['cohort','phase','walls_bin']):
 p=r['global_weight_bin_contributions']['validation'][dim];labels=list(p);vals=[v['models']['standard400']['global_signed_gap_contribution']for v in p.values()];bars=ax.bar(range(len(labels)),vals,color=['#bd4141'if v>=0 else'#248777'for v in vals]);ax.set_xticks(range(len(labels)),labels,rotation=40);ax.axhline(0,color='gray',lw=.7);ax.set_title(dim);ax.set_ylabel('Signed contribution to full validation gap')
 for b,v in zip(bars,p.values()):ax.annotate('mass %.1f%%'%(100*v['weightmass']),(b.get_x()+b.get_width()/2,b.get_height()),ha='center',va='bottom'if b.get_height()>=0 else'top',fontsize=7)
f.suptitle('standard400: original global rowweights, exhaustive label-free bins (exploratory)');f.tight_layout();f.savefig(D/'bin-contributions.png',dpi=140);f.savefig(D/'bin-contributions.svg');plt.close(f)
print('NN0 four figure artifacts')
