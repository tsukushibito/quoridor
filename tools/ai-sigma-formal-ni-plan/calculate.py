import math,json,pathlib,datetime,os,time,resource
D=pathlib.Path('research-data/ai-sigma/158-formal-ni-plan');start=time.monotonic();os.sched_setaffinity(0,{0})
def eps(m):return math.sqrt(math.log(20)/(2*m))
def identify(slots):
 assert len(slots)%2==0 and all(0<=lo<=hi<=1 for lo,hi in slots)
 m=len(slots)//2;low=sum(x[0]for x in slots)/(2*m);high=sum(x[1]for x in slots)/(2*m)
 return {'m':m,'mean_low':low,'mean_high':high,'L':max(0,low-eps(m)),'U':min(1,high+eps(m))}
def binomial_power(m,p):
 threshold=.45+eps(m);kmin=math.floor(m*threshold)+1
 return sum(math.exp(math.lgamma(m+1)-math.lgamma(k+1)-math.lgamma(m-k+1)+k*math.log(p)+(m-k)*math.log1p(-p))for k in range(kmin,m+1))
out={'source':'Hoeffding1963 theorem2, bounded independent pair Xi, one-sided alpha .05','first_plan_m':600,'thresholds':{str(m):{'eps':eps(m),'strict_mean_required':.45+eps(m),'L_if_mean_half':max(0,.5-eps(m))}for m in [8,100,200,600]},'power600':[],'required_m_guarantee':[],'cost':[]}
for mu in [.5,.55,.6]:
 gap=mu-(.45+eps(600));guarantee=max(0,1-math.exp(-2*600*gap*gap))if gap>0 else 0
 out['power600'].append({'mu':mu,'Hoeffding_power_lower_bound':guarantee,'illustrative_IID_Bernoulli_pair_exact_power':binomial_power(600,mu),'true_half_constant_pair_power':1 if mu==.5 else None,'power_not_identified_by_mean_alone':True})
 for power in [.8,.9,.95]:
  n=math.floor((math.sqrt(math.log(20)/2)+math.sqrt(math.log(1/(1-power))/2))**2/(mu-.45)**2)+1
  out['required_m_guarantee'].append({'mu':mu,'power_at_least':power,'strict_sufficient_m':n,'games':2*n})
for m in [600,1198,2047]:
 for parallel in [1,2,4]:out['cost'].append({'pairs':m,'games':2*m,'parallel':parallel,'old_mean_thinking_s':2*m*(353.88/16)/parallel,'worst_thinking_s':2*m*100/parallel,'startup_save_cooling_clock_extra_excluded':True,'speedup_not_measured':True})
mock={'allnormalhalf':identify([(0,0),(1,1)]*600),'allunknown':identify([(0,1)]*1200),'oneknown_win_oneunknown':identify([(1,1),(0,1)]),'candidatefault_referencefault':{'operational_slots':[(0,0),(0,1)],'terminal_quality_slots':[(0,1),(0,1)]},'boundary_strict':(.45+eps(600)-eps(600)>.45)}
assert mock['allunknown']['L']==0 and mock['allunknown']['U']==1
assert mock['oneknown_win_oneunknown']['mean_low']==.5 and mock['oneknown_win_oneunknown']['mean_high']==1
assert .45+eps(100)>.57238 and .45+eps(200)>.53654
out['mock']=mock;out['UTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();out['wall_s']=time.monotonic()-start;out['ru_maxrss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;out['CPU']=[0];out['NN_Chrome_game_build']=0
(D/'numbers.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
