import json,hashlib,math,datetime,sys
from pathlib import Path
ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma');O=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-ENTRY-REPAIR';OLD=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-CONTINUATION-MATCH-PLAN';p=json.loads((O/'preregister.json').read_text());old=json.loads((OLD/'preregister.json').read_text())
def rng(seed):
 x=seed
 def f(n):
  nonlocal x
  lim=(2**32//n)*n
  while True:
   x=(x^(x<<13))&0xffffffff;x=(x^(x>>17))&0xffffffff;x=(x^(x<<5))&0xffffffff
   if x<lim:return x%n
 return f
def shuffle(v,seed):
 v=list(v);r=rng(seed)
 for i in range(len(v)-1,0,-1):j=r(i+1);v[i],v[j]=v[j],v[i]
 return v
exclude=[25,4,51,0,47,44,56,31];eligible=[i for i in range(64) if i not in exclude];selection=shuffle(eligible,2026100301)[:48];order=shuffle(selection,2026100302);colors=rng(2026100303);cr=[]
for i in order:cr.append([2,1] if colors(2) else [1,2])
assert selection==p['selected_indices']==old['selected_indices'];assert order==p['ordered_indices']==old['ordered_indices'];assert cr==[b['candidate_color_order'] for b in p['pairs']];assert p['pairs']==old['pairs'];assert hashlib.sha256((OLD/'preregister.json').read_bytes()).hexdigest()=='05cf461e23998e7e230c05b280a16f4105723cd1b5d4604f28f5374272961002';assert len(set(selection))==48
for i,b in enumerate(p['pairs']):
 assert b['pair']==i+1 and b['pool_index']==order[i]
 for j,g in enumerate(b['games']):assert g['game']==2*i+j+1 and g['candidate_color']==cr[i][j] and g['reference_color']==3-g['candidate_color'] and g['seed']==1979
width=math.sqrt(math.log(20)/96);L=max(0,.5-width);stop=datetime.datetime.fromisoformat('2026-10-02T00:30:00+00:00');latest=stop-datetime.timedelta(seconds=11801.5);assert latest.isoformat()=='2026-10-01T21:13:18.500000+00:00';assert 48*2*200*.5+400+1200+600==11800
mock={}
for name in ['all96','candidate_loss','reference_timeout','one_retry','pair_exhausted','global_exhausted','pause','deadline','signal','no_response','cleanup_pending','pending_old','identity','partial']:
 r=json.loads((O/('diag-'+(sys.argv[1] if len(sys.argv)>1 else 'final3')+'-'+name)/'summary.json').read_text());table=r['table'];pairs=[]
 for b in p['pairs']:
  if all(table[g['game']-1]['status']=='completed' for g in b['games']):pairs.append(sum(table[g['game']-1]['result']['score'] for g in b['games'])/2)
 mean=sum(pairs)/len(pairs) if pairs else None;lower=max(0,mean-width) if len(pairs)==48 else None
 assert len(pairs)==r['score']['completed_pairs'] and mean==r['score']['mean'] and lower==r['score']['L'];assert r['retries']<=2
 from collections import Counter
 counts=Counter(a['pair'] for a in r['attempts']);assert max(counts.values())<=2
 for a in r['attempts']:assert a['prefix_sha256']==p['pairs'][a['pair']-1]['prefix_sha256'] and a['seed']==1979
 mock[name]={'completed_pairs':len(pairs),'mean':mean,'L':lower,'retries':r['retries']}
r={'Python_independent_implementation_same_owner':True,'other_role_acceptance':False,'PRNG_selection_order_colors_exact':True,'pairs_all96_old_exact':True,'width':width,'mean_half_L':L,'minimum_observed_mean_for_exploratory_L45':.45+width,'latest_startUTC':latest.isoformat(),'minimum_budget_s':11801.5,'mock_scores_retries_checked':mock,'NN':0,'games':0,'actual_go':False};(O/'python-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='mock_scores_retries_checked'}))
