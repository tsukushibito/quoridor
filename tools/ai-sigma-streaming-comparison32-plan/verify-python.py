import json,math,hashlib,datetime
from pathlib import Path
ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma');O=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-COMPARISON32-PLAN';OLD=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-CONTINUATION-MATCH-PLAN';read=lambda p:json.loads(p.read_text());p=read(O/'preregister.json');dictionary=read(O/'prefix-dictionary.json');node=read(O/'node-verification.json');pool=read(OLD/'snapshot/pool64.json');assert hashlib.sha256((O/'prefix-dictionary.json').read_bytes()).hexdigest()==p['prefix_dictionary']['sha256']
def rng(seed):
 x=seed;trace=[]
 def draw(n):
  nonlocal x
  lim=(2**32//n)*n;rejected=0
  while True:
   x=(x^(x<<13))&0xffffffff;x=(x^(x>>17))&0xffffffff;x=(x^(x<<5))&0xffffffff
   if x<lim:break
   rejected+=1
  i=x%n;trace.append({'n':n,'v':x,'limit':lim,'rejected':rejected,'index':i});return i
 return draw,trace
def shuffle(values,draw):
 a=list(values)
 for i in range(len(a)-1,0,-1):j=draw(i+1);a[i],a[j]=a[j],a[i]
 return a
eligible=[i for i in range(64) if i not in [25,4,51,0,47,44,56,31]];sr,st=rng(2026100501);selected=shuffle(eligible,sr)[:32];orng,ot=rng(2026100502);ordered=shuffle(selected,orng);cr,ct=rng(2026100503);colors=[[2,1] if cr(2) else [1,2] for i in ordered];assert selected==p['selected_indices']==node['selection'];assert ordered==p['ordered_indices']==node['order'];assert colors==node['colors'];assert {'selection':st,'order':ot,'color':ct}==read(O/'extraction-trace.json')
nums=[]
for i,b in enumerate(p['pairs']):
 assert b['pair']==i+1 and b['pool_index']==ordered[i] and b['candidate_color_order']==colors[i];d=dictionary[b['prefix_ref']];f=pool['pool'][ordered[i]];assert d['legal_prefix']==f['legal_prefix'] and d['rust_prefix']==f['rust_prefix'] and d['context']==f['context'];assert d['context']['remaining_total_ply']==200-len(d['legal_prefix']);assert d['context']['terminal'] is None
 for j,g in enumerate(b['games']):assert g['game']==2*i+j+1 and g['candidate_color']==colors[i][j] and g['reference_color']==3-g['candidate_color'] and g['seed']==1979;nums.append(g['game'])
assert nums==list(range(1,65));assert len(set(ordered))==32;assert len(dictionary)==32
width=math.sqrt(math.log(20)/64);worst=64*200*.5+400+1200+600;stop=datetime.datetime.fromisoformat('2026-10-02T00:30:00+00:00');latest=stop-datetime.timedelta(seconds=worst+1.5);assert worst==8600 and latest.isoformat()=='2026-10-01T22:06:38.500000+00:00';assert abs(width-node['width'])<1e-15
# Independently implement control-plan arithmetic. No engine fault classifier or backend.
def simulate(mode):
 retry=0;reason=None;Xi=[];attempts=[]
 for pair in p['pairs']:
  valid=False
  for attempt in range(2):
   a={'pair':pair['pair'],'attempt':attempt,'prefix_ref':pair['prefix_ref'],'seed':1979,'game_numbers':[],'scores':[],'invalid':False};attempts.append(a)
   for g in pair['games']:
    if mode in ['pause','guard','deadline','signal'] and g['game']==4:reason=mode;break
    a['game_numbers'].append(g['game'])
    invalid=(mode=='one_invalid' and pair['pair']==1 and attempt==0) or (mode=='pair_exhausted' and pair['pair']==1) or (mode=='global_exhausted' and pair['pair']<=3 and attempt==0)
    if invalid:a.update(invalid=True,invalid_control='prescribed pair invalid');break
    v=0 if mode=='candidate_loss' else 1 if mode=='reference_loss' else .5 if mode=='all_draw' else 1 if g['candidate_color']==1 else 0;a['scores'].append(v)
   if reason:break
   if not a['invalid'] and len(a['scores'])==2:Xi.append(sum(a['scores'])/2);valid=True;break
   if a['invalid'] and attempt==0 and retry<2:retry+=1;continue
   reason='retry_exhausted';break
  if reason or not valid:break
 mean=sum(Xi)/len(Xi) if Xi else None;score={'planned_m':32,'completed_pairs':len(Xi),'complete':len(Xi)==32,'mean':mean,'L':max(0,mean-width) if len(Xi)==32 else None}
 return {'mode':mode,'retries':retry,'stop':reason,'score':score,'attempts':attempts,'actual_go':False,'scope':'prescribed control-plan arithmetic; not backend/main/classification gate'}
scenarios=read(O/'compact-scenarios.json');diffs={}
for mode,n in scenarios.items():
 q=simulate(mode);assert q['attempts']==n['attempts'] and q['retries']==n['retries'] and q['stop']==n['stop'] and q['score']==n['score'];assert q['retries']<=2
 counts={}
 for a in q['attempts']:counts[a['pair']]=counts.get(a['pair'],0)+1
 assert all(v<=2 for v in counts.values());diffs[mode]={'exact':True,'completed_pairs':q['score']['completed_pairs'],'retries':q['retries'],'L':q['score']['L'],'stop':q['stop']}
assert scenarios['all64']['score']['mean']==.5;assert scenarios['all_draw']['score']['mean']==.5;assert scenarios['candidate_loss']['score']['mean']==0;assert scenarios['reference_loss']['score']['mean']==1;assert scenarios['one_invalid']['retries']==1;assert scenarios['global_exhausted']['retries']==2
m_precision=math.ceil(math.log(20)/(2*.05**2));m_power=math.ceil((math.sqrt(math.log(20))+math.sqrt(math.log(5)))**2/(2*.05**2));serfling=math.sqrt((1-(32-1)/56)*math.log(20)/64)
proposals=[{'alternative':'predeclared distribution-free paired Hoeffding precision','m_pairs':m_precision,'games':2*m_precision,'worst_thinking_s':m_precision*200,'fixed_overhead_s':2200,'conditions':'fixed valid bounded pairs; assumptions justify confidence; threshold width.05 only, not power guarantee','risks':'beyond current pool56/global window, new pool/training audit/resources required'}, {'alternative':'80% power conservative sufficient bound at true pair mean.5, one-sided alpha.05','m_pairs':m_power,'games':2*m_power,'worst_thinking_s':m_power*200,'formula':'(sqrt(log20)+sqrt(log5))^2/(2*.05^2)','conditions':'bounded independent/fixed sampling assumptions; sufficient not minimal; new separate contract only','risks':'far exceeds time and population; not added to current evaluator'}, {'alternative':'finite-population Serfling reference for old eligible56','illustrative_width_m32':serfling,'mean_half_L':max(0,.5-serfling),'extra_games_to_census56':48,'extra_thinking_s':4800,'conditions':'fixed potential Xi for finite56 and valid without-replacement uniform sample; sequence-dependent/noisy games may violate assumptions','risks':'finite pool only, not general/native/browser NI; not applied to m32 score'}, {'alternative':'predeclared paired empirical-Bernstein/exact discrete or bootstrap sensitivity','m_pairs':None,'cost':'separate method validation and independent pilot design; do not reuse current outcomes to choose CI','conditions':'validate coverage/correlation/clock-order effects and target population first','risks':'bootstrap not guaranteed coverage at n32; treating64 games independent is invalid'}]
r={'Python_PRNG_arithmetic_separate_implementation':True,'same_owner_not_other_role_acceptance':True,'selection32_order_colors_64_numbers_exact':True,'PRNG_trace_exact':True,'compact11_scenarios_exact':diffs,'dict32_no_duplicate_prefix_payload':True,'width':width,'mean_half_L':max(0,.5-width),'minimum_mean_for_L45':.45+width,'worst8600_s':worst,'reserve_s':1.5,'latest_start_UTC':latest.isoformat(),'below_minimum_reject_at_latest_plus1ms':True,'minimum_entry_not_tail_guarantee':True,'NI_not_established':True,'future_CI_power_proposals':proposals,'actual_go':False,'NN':0,'engine':0,'games':0};(O/'python-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['compact11_scenarios_exact','future_CI_power_proposals']}))
