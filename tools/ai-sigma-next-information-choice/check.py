import json,pathlib,hashlib,itertools,statistics,os,datetime
D=pathlib.Path('research-data/ai-sigma/139-next-information-choice');refs={}
def load(p):
 p=pathlib.Path(p);raw=p.read_bytes();refs[str(p)]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
plan=load(D/'next-experiment-v1.json');assert plan['max_next_experiments']==1 and plan['actual_go'] is False
assert plan['stageA']['searches_max']*plan['stageA']['K']==plan['stageA']['hand_NN_max']==192
assert plan['stageB_quality_exit']['rollouts_max']*200*.5==plan['stageB_quality_exit']['worst_think_seconds']==800
assert plan['stageB_quality_exit']['rollouts_max']*180==plan['stageB_quality_exit']['runtime_wall_budget_seconds']==1440
assert 45+2+2+24+15==plan['cost_estimate']['wall_worst_minutes']==88
a=load('research-data/ai-sigma/137-fixed-policy-cost/analysis.json');h=load('research-data/ai-sigma/137-fixed-policy-cost/handoff-summary.json');old=load('research-data/ai-sigma/136-policy-factor-choice/analysis.json');quality=load('research-data/ai-sigma/134-local-move-quality/final-results.json');q135=load('research-data/ai-sigma/135-local-move-independent/all-independent.json')
rows=[];pairs=[]
for s in a['samples']:
 cp=s['CP_series'];assert [c['K'] for c in cp]==list(range(1,s['adopted_eligible_completed_backup']+1));assert cp[-1]['Action']==s['Action209'];ds=s['API_await_durations_ms'];assert abs(statistics.median(ds)-s['API_await_median_ms'])<=.00002
 changes=[{'K':n['K'],'before':p['Action'],'after':n['Action']} for p,n in zip(cp,cp[1:]) if n['Action']!=p['Action']]
 rows.append({'id':s['sample'],'warm':s['warm'],'adoptedK':cp[-1]['K'],'Action':cp[-1]['Action'],'API_median':statistics.median(ds),'action_change_points':changes,'clock_wait_not_CPU':True})
for l,r in itertools.combinations(a['samples'],2):
 lc={v['K']:v['Action'] for v in l['CP_series']};rc={v['K']:v['Action'] for v in r['CP_series']};common=sorted(lc.keys()&rc.keys());equal=all(lc[k]==rc[k] for k in common);assert equal;pairs.append({'samples':[l['sample'],r['sample']],'commonK':common,'Action_same':equal})
assert [r['adoptedK'] for r in rows]==h['eligible_backups'];assert [r['Action'] for r in rows]==h['Actions']
score=[]
for g in quality['games']:
 v=1 if g['winner']==g['forced_side'] else .5 if g['winner'] is None else 0
 match=next(r for r in q135['games'] if r['id']==g['id']);assert v==match['score'];score.append({'id':g['id'],'score':v,'policy':'both fixedSigma, forced first from K32 root'})
roots=[r for r in old['roots132'] if r['engine']=='candidate'];assert len(roots)==2
assert roots[0]['max_visit_ties'][0]['action']==133 and roots[0]['finish_first_same_order']==133 and roots[0]['action']==161
assert all(r['visited']==r['visited_parentQ_negative'] for r in roots)
x={'issue':'quoridor-4lc.139','run':os.environ.get('SIGMA_INFORMATION_RUN'),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'samples':rows,'pairwise_commonK':pairs,'CP_series_entries':sum(len(s['CP_series']) for s in a['samples']),'pairwise_K_comparisons':sum(len(p['commonK']) for p in pairs),'Action_reverses':'sample3 162->154->162; moreK not monotonic quality evidence','scores134_vs135':score,'FPU_missing_parentQ':all(r['parentQ_missing'] for r in roots),'finish_first_counterexample':'161->133 on old input3 chooses lower fixedSigma continuation score','input_hashes':refs,'new_raw_roots':0,'plan_arithmetic':{'max_searches':6,'stageA_NN_bound':192,'conditional_rollouts_max':8,'stageB_think_bound_s':800,'runtime_job_caps_total_s':1560,'implementation_build_runtime_review_worst_minutes':88,'plan_not_permission':True},'claim_limits':'own arithmetic on saved summaries; no independent raw CP-edge bits/NN/replay/CPU validation','NN':0,'actual_go':False}
(D/'information-check.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'samples':rows,'CP_series_entries':x['CP_series_entries'],'pairwise_K_comparisons':x['pairwise_K_comparisons'],'new_raw_roots':0},ensure_ascii=False))
