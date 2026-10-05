import json, pathlib, tarfile, math, hashlib, datetime, struct
BASE=pathlib.Path('research-data/ai-sigma')
OUT=BASE/'130-deep-discrimination'
refs={}
def read(p):
 p=pathlib.Path(p); refs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def raw(task,archive):
 p=BASE/task/archive
 refs[str(p)]=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
 with tarfile.open(p) as t:
  m=next(m for m in t if m.name.endswith('browser-result.json'))
  return json.load(t.extractfile(m))
def finite(n):
 assert len(n['features_bits'])==648 and len(n['policy_logits'])==136
 assert all(math.isfinite(v) for v in n['policy_logits']) and math.isfinite(n['value']) and -1<=n['value']<=1
f=read(BASE/'129-tactical-evaluation/final-results.json')
x=raw('129-tactical-evaluation','runs-all-attempts.tar.gz')
metrics=f['metrics'];assert len(metrics)==12
normal=[m for m in metrics if m['spec']['condition'] in ['A','B']]
stress=[m for m in metrics if m['spec']['condition']=='S']
sums={k:sum(m['adopted_stats'][k] for m in normal) for k in ['completed_backup','cp_NN_calls','terminal_noNN_backup']}
assert sums=={'completed_backup':276,'cp_NN_calls':61,'terminal_noNN_backup':215}
assert sum(m['hand_NN'] for m in metrics)==71
assert len(stress)==4 and all(m['adopted_stats']['cp_NN_calls']==1 and m['adopted_stats']['edge_sum']==0 for m in stress)
assert sum(m['private_result_error']=='STALE_GENERATION' for m in metrics)==6
assert not any(m['public_causes']['received_engine_fault'] for m in metrics)
roots=[]
for r in x['rows']:
 if r['spec']['condition']!='A':continue
 case=r['spec']['case'];cp=r['diagnostic']['validated_cp'];n=r['diagnostic']['numeric'][0];finite(n)
 edges=cp['root_edges'];top=sorted(edges,key=lambda e:e[1],reverse=True)
 assert top[0][1]>top[1][1] and cp['action']==top[0][0]
 assert sum(e[2] for e in edges)+1==cp['simulations']
 assert not cp['policy_fallbacks'] and not cp['value_fallbacks']
 a=next(m for m in normal if m['spec']['case']==case and m['spec']['condition']=='A')
 s=next(m for m in stress if m['spec']['case']==case)
 assert a['Action']==s['Action']
 roots.append({'case':case,'action209':cp['action'],'top_prior':top[0][1],'next_prior':top[1][1],'unique_prior_argmax':True,'normal_equals_stress_action':True,'normal_backup':cp['simulations'],'normal_CP_NN':cp['nn_calls'],'normal_max_depth':cp['max_depth'],'rootN':'conditional sim=edge_sum+1; raw root node visits absent','root_features_SHA':hashlib.sha256(struct.pack('<648I',*n['features_bits'])).hexdigest()})
assert len(roots)==4
pairs=[]
for pair in [1,2]:
 x=raw('119-diverse-prefix',f'prefix119-pair{pair}-r1.tar.gz')
 rows=[r for r in x['rows'] if r['spec']['turn']==0]
 assert len(rows)==2 and {r['spec']['engine'] for r in rows}=={'candidate','reference'}
 a=next(r for r in rows if r['spec']['engine']=='candidate');b=next(r for r in rows if r['spec']['engine']=='reference')
 for r in rows:finite(r['diagnostic']['numeric'][0])
 na=a['diagnostic']['numeric'][0];nb=b['diagnostic']['numeric'][0]
 assert na==nb
 assert struct.pack('<137f',*na['policy_logits'],na['value'])==struct.pack('<137f',*nb['policy_logits'],nb['value'])
 assert all(a['identity'][k]==b['identity'][k] for k in ['key','history','legal_prefix','model'])
 # Record same saved initial decision only; no later roots or whole-game replay.
 pairs.append({'pair':pair,'same_initial_features_logits_value':True,'same_key_history_prefix_model':True,'same_Action':a['response']['body']['action']==b['response']['body']['action'],'candidate_action209':a['diagnostic']['validated_cp']['action'],'reference_public_action':b['response']['body']['action'],'candidate_CP_NN':a['diagnostic']['validated_cp']['nn_calls'],'reference_CP_NN':b['diagnostic']['validated_cp']['nn_calls'],'later_divergence':'unobserved in this checker; no deep trace/parentQ inferred'})
for p in ['tools/ai-sigma-ort-search/src/kernel.rs','tools/ai-sigma-actual-boundary-repair/reference-core.js']:
 refs[p]=hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
out={'issue':'quoridor-4lc.130','run':'saved130-r1','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'normal129':sums,'terminal_noNN_fraction':215/276,'stress129':{'n':4,'CP_NN_each':1,'edge_sum_each':0,'same_normal_action_all':True},'private_STALE':6,'public_engine_fault':0,'roots129_A_only':roots,'roots119_turn0_only':pairs,'root_read_denominators':{'129':4,'119':4},'NN':0,'games':0,'missing':['candidate parentQ','child/deep NN trace','kernel CPU','general strategic oracle'],'actual_go':False,'input_hashes':refs}
(OUT/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['input_hashes']},ensure_ascii=False))
