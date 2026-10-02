import math,json,datetime,os,time,resource,hashlib
from pathlib import Path
O=Path('.artifacts/ai-sigma/resume-20261002/FRAME8-EVALUATION-PLAN');O.mkdir(exist_ok=True)
def h(n,a):return math.sqrt(math.log(1/a)/(2*n))
def eb(n,a,v):return math.sqrt(2*v*math.log(2/a)/n)+7*math.log(2/a)/(3*(n-1))
def first(pred):
 n=2
 while not pred(n):n+=1
 return n
rows=[]
for a in [.05,.025,.0125]:
 n=first(lambda n:h(n,a)<.05)
 power=first(lambda n:h(n,a)+h(n,.2)<.05)
 ebrows=[]
 for v in [0,.0625,.125,.25]:
  k=first(lambda n:eb(n,a,v)<.05);ebrows.append({'hypothetical_observed_sample_variance':v,'n_width_below_05':k,'not_power_guarantee':True,'wall_hours_330n_plus1200':(330*k+1200)/3600})
 ep=first(lambda n:eb(n,a,n/(4*(n-1)))+h(n,.2)<.05)
 rows.append({'alpha':a,'Hoeffding_n_width_below_05':n,'Hoeffding_conservative_80pct_n':power,'Hoeffding_conservative_90pct_n':first(lambda n:h(n,a)+h(n,.1)<.05),'Hoeffding_hours_one_environment':(330*n+1200)/3600,'EB_variance_scenarios':ebrows,'EB_universal_conservative_80pct_n':ep,'EB_universal_conservative_90pct_n':first(lambda n:eb(n,a,n/(4*(n-1)))+h(n,.1)<.05)})
newstart=datetime.datetime.fromisoformat('2026-10-02T10:15:49+00:00');stop=datetime.datetime.fromisoformat('2026-10-02T14:05:49+00:00');receipt=datetime.datetime.fromisoformat('2026-10-02T10:32:31+00:00');after115=datetime.datetime.fromisoformat('2026-10-02T11:30:00+00:00')
budgets=[]
for label,start in [('frame_start',newstart),('receipt',receipt),('hypothetical_after_115_deadline',after115)]:
 seconds=(stop-start).total_seconds();m=max(0,int((seconds-1200)//330));budgets.append({'from':label,'seconds_before_new_heavy_stop':seconds,'planning_pairs_max':m,'mean_half_old_L':max(0,.5-h(m,.05)) if m else None,'overhead_is_explicit_planning_cap_not_measured':True})
obs=json.loads(Path('research-data/ai-sigma/112-player-workers/results-compact.json').read_text());games=obs['games'];observedply=[g['total_ply']-(0 if 'initial' in g['id'] else 3) for g in games]
j={'issue':'quoridor-4lc.116','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tables':rows,'budget':budgets,'pair_scoring':{'Xi':'(game1score+game2score)/2','range':[0,1],'possible_values':[0,.25,.5,.75,1]},'old_m32_width':h(32,.05),'observed_112_newplies':observedply,'observed_112_mean_newplies':sum(observedply)/len(observedply),'observed_112_nominal_500ms_sum':sum(observedply)*.5,'max_newply_game':200,'nominal_pair_adoption_allotment_s':200,'pair_wall_cap_s':300,'pair_owned_cleanup_reserve_s':30,'common_setup_final_reserve_s':1200,'GPU_speed_assumed':False,'iidx_assumption_not_validated':True}
# Math checks address signs, finite denominators and strict NI threshold, not an implementation-only unit suite.
assert abs(j['old_m32_width']-.216352297825)<1e-12
for r in rows:
 n=r['Hoeffding_n_width_below_05'];assert h(n,r['alpha'])<.05<=h(n-1,r['alpha'])
 assert all(eb(e['n_width_below_05'],r['alpha'],e['hypothetical_observed_sample_variance'])<.05 for e in r['EB_variance_scenarios'])
# pair arithmetic with all valid non-score outcomes excluded from formal completion, never converted to losses.
scenarios=[{'name':'oneWinOneLoss','scores':[1,0],'Xi':.5},{'name':'twoDraw','scores':[.5,.5],'Xi':.5},{'name':'partial','scores':[1,None],'Xi':None},{'name':'infra','scores':[None,None],'Xi':None}]
for s in scenarios:assert s['Xi']==(None if None in s['scores'] else sum(s['scores'])/2)
j['scenarios']=scenarios;(O/'arithmetic.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps({'tables':rows,'budget':budgets,'observed':observedply},indent=2))
