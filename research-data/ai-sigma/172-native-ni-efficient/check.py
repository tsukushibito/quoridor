from fractions import Fraction as F
import math,json,pathlib,hashlib,datetime
D=pathlib.Path(__file__).parent
PLUS=[F(1,4),F(1,2),F(1),F(3,2),F(2)];MINUS=PLUS[:-1];THETA=F(9,20)
def wealth(ys,direction=1):
 lambdas=PLUS if direction==1 else MINUS;w=[F(1)]*len(lambdas)
 for y in ys:
  assert F(0)<=y<=F(1)
  for j,l in enumerate(lambdas):
   factor=1+direction*l*(y-THETA);assert factor>=0;w[j]*=factor
 return sum(w)/len(w)
def logwealth(ys,direction=1):
 lambdas=PLUS if direction==1 else MINUS;logs=[sum(math.log1p(float(direction*l*(y-THETA))) for y in ys) for l in lambdas];m=max(logs);return m+math.log(sum(math.exp(v-m) for v in logs))-math.log(len(logs))
def block(games):
 assert len(games)==6
 low=[];high=[]
 for g in games:
  if g['status']=='TERMINAL_VALID':
   s=F(g['score']);assert s in [F(0),F(1,2),F(1)];low.append(s);high.append(s)
  else:low.append(F(0));high.append(F(1))
 return sum(low)/6,sum(high)/6
# Synthetic demonstrations, no sampled AI WDL and no Monte Carlo.
checks=[]
for y in [F(0),F(1,2),F(1)]:
 ys=[y]*200;w=wealth(ys);assert abs(logwealth(ys)-math.log(float(w)))<1e-10
 first=next((n for n in range(1,201) if wealth(ys[:n])>=20),None)
 checks.append({'synthetic_constant_Y':str(y),'first_NI_block':first,'games_started_if_cross':first*6 if first else 1200,'end_plus_log':logwealth(ys),'end_minus_log':logwealth(ys,-1)})
# Pathwise monotonicity of nonnegative factors, including missingness depending on outcome.
low=[F(0),F(1,2),F(1,4)];true=[F(1,3),F(1,2),F(2,3)];high=[F(1),F(1,2),F(3,4)]
assert wealth(low)<=wealth(true)<=wealth(high);assert wealth(high,-1)<=wealth(true,-1)<=wealth(low,-1)
lo,hi=block([{'status':'TERMINAL_VALID','score':'1'}]*5+[{'status':'CLOCK_UNKNOWN'}]);assert lo==F(5,6) and hi==1
# A missing registered block is not bypassed; future slots after STOP are not observations.
prefix=[F(1)]*6;before=wealth(prefix);first=next(n for n in range(1,7) if wealth(prefix[:n])>=20)
assert first is not None;future_wealth=wealth(prefix[:first]);zero_padded=wealth(prefix[:first]+[F(0)]*(200-first));assert future_wealth>=20 and zero_padded<future_wealth
unknown_block=[F(0)];assert wealth(unknown_block)==wealth([F(0)])
# Conditional null inequality endpoints: average score <=.45 gives conditional expected factor <=1.
for l in PLUS:
 for mu in [F(0),F(1,4),THETA]:assert 1+l*(mu-THETA)<=1
for l in MINUS:
 for mu in [THETA,F(1,2),F(1)]:assert 1-l*(mu-THETA)<=1
# All marginal means equal .45 is insufficient: common latent Z repeated across blocks.
latent_cross=next(n for n in range(1,201) if wealth([F(1)]*n)>=20)
# Exact threshold arithmetic at attainable Y=k/12, denominator240.
for k in range(13):
 for a,l in zip([1,2,4,6,8],PLUS):assert 1+l*(F(k,12)-THETA)==F(240+a*(5*k-27),240)
# Input/resource cost examples only, never infer multiplier from 40 short requests.
base=F(431553877,1000000)/16 # saved UTC job endpoint total /16, seconds per game
cost={'saved_native16_job_s':float(base*16),'mean_job_s_per_game':float(base),'max1200_solo_hours':float(base*1200/3600),'ideal_three_parallel_hours':float(base*1200/(3*3600)),'worst_200ply_500ms_1200_ideal_three_hours':1200*100/(3*3600),'ideal_block_seconds':float(base*2),'remaining_parent_s_from_receipt':(datetime.datetime(2026,10,3,8,15,21,tzinfo=datetime.timezone.utc)-datetime.datetime.fromisoformat(json.loads((D/'intake.json').read_text())['received'])).total_seconds(),'three_mode_wholegame_measured':False}
# Independent Xi Bernoulli(p) illustration gives Y=Binomial(3,p)/3; expected log is NOT power.
growth=[]
for p in [.5,.55,.6]:
 g=[]
 for l in PLUS:
  value=sum(math.comb(3,k)*p**k*(1-p)**(3-k)*math.log1p(float(l)*(k/3-.45)) for k in range(4));g.append({'lambda':float(l),'expected_log_increment':value,'200block_expected_component_log':200*value})
 growth.append({'assumed_independent_Bernoulli_pair_mean':p,'components':g,'not_power_or_stopping_time':True})
out={'issue':'quoridor-4lc.172','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_SHA':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'new_formal_data':0,'NN':0,'core_pool':[2,4,6],'pairs_per_block':3,'max_blocks':200,'max_games':1200,'lambda_plus':[float(v) for v in PLUS],'lambda_minus':[float(v) for v in MINUS],'threshold':20,'synthetic_checks':checks,'unknown_example':{'five_wins_one_clock_unknown_low':str(lo),'high':str(hi)},'post_threshold_future_slots_not_wealth':True,'latent_dependence_counterexample':{'all_marginal_means':.45,'Z_1_prob':.45,'cross_on_Z1_block':latent_cross,'false_support_prob':.45,'conditional_null_not_satisfied':True},'cost':cost,'growth':growth,'all_assertions_passed':True,'exact_Fraction_is_decision_authority':True,'float_logsumexp_diagnostic_only':True}
(D/'check-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
