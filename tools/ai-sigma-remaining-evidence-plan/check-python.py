import json,math,hashlib,datetime
from pathlib import Path
A=Path('.artifacts/ai-sigma/continuation-20261001/SIGMA-REMAINING-EVIDENCE-PLAN')
p=json.loads((A/'evidence-choice-plan.json').read_text());node=json.loads((A/'node-static-check.json').read_text());assert not p['m8_adopted'] and not p['actual_go'] and not p['new_prefix_selection']
def scenario(kind):
 attempts=[];pairs=[];retries=0;stop=None
 for pair in range(8):
  if kind in ('pause','deadline','signal','guard') and pair==3:stop=kind.upper();break
  done=False
  for attempt in range(2):
   bad=(kind=='one_invalid' and pair==0 and attempt==0) or (kind=='pair_exhausted' and pair==0) or (kind=='global_exhausted' and pair<3 and attempt==0)
   attempts.append(dict(synthetic_pair=pair,attempt=attempt,invalid=bad,control_symbol='invalid_pair' if bad else 'two_scores',prefix=None))
   if bad:
    if attempt:stop='PAIR_RETRY_EXHAUSTED';break
    if retries>=2:stop='GLOBAL_RETRY_EXHAUSTED';break
    retries+=1;continue
   if kind=='candidate_loss':scores=[0,0]
   elif kind=='reference_loss':scores=[1,1]
   elif kind=='mixed':scores=([1,.5],[0,.5],[1,0],[.5,.5])[pair%4]
   else:scores=[.5,.5]
   pairs.append(dict(synthetic_pair=pair,scores=scores,Xi=sum(scores)/2));done=True;break
  if not done:break
 count=len(pairs);mean=sum(x['Xi'] for x in pairs)/count if count else None
 return dict(kind=kind,attempts=attempts,pairs=pairs,retries=retries,completed=count,planned=8,complete=count==8,mean=mean,L=max(0,mean-math.sqrt(math.log(20)/16)) if count==8 else None,stop=stop,synthetic=True,actual_games=0)
rows=[scenario(k) for k in ('all_draw','candidate_loss','reference_loss','mixed','one_invalid','pair_exhausted','global_exhausted','pause','deadline','signal','guard')];assert rows==node['scenarios']
width=math.sqrt(math.log(20)/(2*8));joint=math.sqrt(math.log(40)/(2*8));assert abs(width-node['interval']['one_sided95_each_width'])<1e-15
stop=datetime.datetime(2026,10,2,0,30,tzinfo=datetime.timezone.utc);terms=[8*2*200*.5,400,1200,600];total=sum(terms);latest=stop-datetime.timedelta(seconds=total+1.5)
assert total==3800 and latest.isoformat(timespec='milliseconds').replace('+00:00','Z')==node['budget']['latest'];assert (stop-(latest+datetime.timedelta(milliseconds=1))).total_seconds()<3801.5
n=math.ceil(math.log(1/.05)/(2*.05*.05));power=math.ceil((math.sqrt(math.log(1/.05))+math.sqrt(math.log(1/.2)))**2/(2*.05*.05));assert n==node['future']['precision_pairs']==600 and power==node['future']['power_sufficient_pairs']==1800
# Probabilistic assumptions are NOT established by this arithmetic check.
comparison=[{'m':m,'one_sided_width':math.sqrt(math.log(20)/(2*m)),'L_if_mean_half':max(0,.5-math.sqrt(math.log(20)/(2*m))),'worst_think_s':m*200} for m in [8,32,48,600,1800]]
assumptions=['Xi bounded[0,1] and unit is color-swapped pair, not individual game','independence or valid random finite-population model must be independently adjudicated','received-order/temporal residuals can correlate pairs and engine assignment; bootstrap alone does not cure','two separate95% one-sided bounds imply at least90% simultaneous coverage via union bound; Bonferroni ln40 gives95% joint under same assumptions','reference U below.45 can indicate inferiority only if bound assumptions hold; L below.45 is absence of proof not proof of inferiority','even all8 wins gives reference L~.567 but does not prove native+browser or formal NI without validated assumptions; no favorable-result dependent choice','formal power sample1800 is sufficient conservative bound, not exact/minimum or applied test']
result={'all_static_assertions_passed':True,'same_owner_two_languages_not_other_role_acceptance':True,'node_python_scores_retry_attempts_denominators_exact':True,'scenario_count':len(rows),'width':width,'L_half':.5-width,'U_half':.5+width,'mean_to_reference_lower45':.45+width,'joint95_width':joint,'joint95_half':[max(0,.5-joint),min(1,.5+joint)],'budget_seconds':total,'latest':latest.isoformat(timespec='milliseconds'),'plus1ms_no_go':True,'comparison':comparison,'formal_assumptions':assumptions,'CI_alternatives':{'paired_discrete':'Xi grid0,.25,.5,.75,1; exact distribution method needs prespecified nuisance coverage under validated iid, not naive binomial16games','empirical_variance':'valid empirical-Bernstein/confidence sequence may sharpen with sufficient variance evidence, finite coverage and optional-stopping proof; no posthoc chosen CI','finite_population':'Serfling-type narrowing pertains to56 fixed potential pair outcomes only; repeated/order-dependent engine outcomes may violate fixed-value assumption; no broad strength generalization','bootstrap':'m8 paired resampling fragile tail coverage and not formal NI without coverage validation'},'m8_rejected':True,'new_PRNG_draw':False,'new_prefix_dictionary':False,'reason_for_no_draw':'m8 not adopted under conditional contract, preventing accidental holdout selection/commitment; seed values are counterfactual only','current_goal_achieved':False,'NN':0,'games':0,'holdout_sends':0,'actual_go':False}
(A/'python-static-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'all_static_assertions_passed':True,'width':width,'L_half':.5-width,'U_half':.5+width,'budget':total,'latest':latest.isoformat(),'m8_rejected':True,'NN':0}))
