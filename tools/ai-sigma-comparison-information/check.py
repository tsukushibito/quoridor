"""NN0 saved-pair arithmetic; at most eight initial request roots, no replay."""
import json, hashlib, tarfile, statistics, math, datetime, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'research-data/ai-sigma/121-comparison-information'
refs={}
def read(p):
    p=ROOT/p; b=p.read_bytes(); refs[str(p.relative_to(ROOT))]=hashlib.sha256(b).hexdigest()
    return json.loads(b)
def cohort(base,stem,n,lengths):
    rows=[]
    for i in range(1,n+1):
        d=read(f'research-data/ai-sigma/{base}/{stem}-pair{i}-r1.summary.json')
        g=d['games'];assert len(g)==2 and [x['candidate_color'] for x in g]==[1,2]
        assert all(x['status']=='terminal' and x['reason']=='goal' for x in g)
        scores=[{'W':1,'D':.5,'L':0}[x['candidate_result']] for x in g]
        assert all(s==float(x['winner']==x['candidate_color']) for s,x in zip(scores,g))
        assert all(x['total_ply']-lengths[i-1]==x['attempt_public'] for x in g)
        assert sum(x['attempt_public'] for x in g)==d['public']
        e=d['engines'];assert sum(x['public'] for x in e.values())==d['public']
        assert sum(x['hand_NN'] for x in e.values())==d['hand_NN']
        rows.append({'pair':i,'source_Git':d['code_Git'],'prefix_ply':lengths[i-1],
          'Xi':sum(scores)/2,'candidate_results':[x['candidate_result'] for x in g],
          'winner_sides':[x['winner'] for x in g],'same_side_wins':g[0]['winner']==g[1]['winner'],
          'total_ply':[x['total_ply'] for x in g], 'new_public':[x['attempt_public'] for x in g],
          'ply_color2_minus_color1':g[1]['total_ply']-g[0]['total_ply'],
          'engines':{k:{'public':v['public'],'hand_NN':v['hand_NN'],
            'calls_per_public':v['hand_NN']/v['public'],
            'completed_NN_median':v['cp_completed_NN']['median'],
            'completed_NN_n':v['cp_completed_NN']['n'],
            'first_CP_median_ms':v['first_completed_publication_ms']['median']}
            for k,v in e.items()}})
    total={k:{'public':sum(r['engines'][k]['public'] for r in rows),
              'hand_NN':sum(r['engines'][k]['hand_NN'] for r in rows)} for k in ['candidate','reference']}
    for k,v in total.items():v['calls_per_public']=v['hand_NN']/v['public']
    return {'pairs':rows,'pair_n':n,'game_n':2*n,'Xi_mean':statistics.mean(r['Xi'] for r in rows),
      'Xi_population_variance':statistics.pvariance(r['Xi'] for r in rows),
      'same_side_pair_n':sum(r['same_side_wins'] for r in rows),'totals':total,
      'NOTE':'Different trajectories; NN starts are not accepted completed evaluations; medians cannot be averaged into pooled medians.'}

pd=read('research-data/ai-sigma/119-diverse-prefix/prefix-document.json')
plan=read('research-data/ai-sigma/119-diverse-prefix/preregister.json')
assert plan['prefix_SHA256']==refs['research-data/ai-sigma/119-diverse-prefix/prefix-document.json']
lengths=[len(x['fixture']['legal_prefix']) for x in pd['prefixes']]
old=cohort('117-cpu-sigma-comparison','cpu117',6,[0,3,7,0,3,7])
new=cohort('119-diverse-prefix','prefix119',8,lengths)
# Selected by ordinal before root access, not by which engine wins.
selection=read('research-data/ai-sigma/121-comparison-information/root-selection.json')
roots=[];matches=[]
for pair in selection['selected_pairs']:
    p=ROOT/f'research-data/ai-sigma/119-diverse-prefix/prefix119-pair{pair}-r1.tar.gz'
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    refs[str(p.relative_to(ROOT))]=h.hexdigest()
    with tarfile.open(p,'r:gz') as t:
        m=next(x for x in t if x.name.endswith('/browser-result.json'))
        d=json.load(t.extractfile(m))
    for gid in [f'pair{pair}-color1',f'pair{pair}-color2']:
        for eng in ['candidate','reference']:
            r=next(x for x in d['rows'] if x['spec']['game_id']==gid and x['identity']['engine']==eng)
            q=r['diagnostic'];cp=q['validated_cp'];num=q['numeric'][0];identity=r['identity']
            assert len(num['features_bits'])==648 and len(num['policy_logits'])==136
            assert all(math.isfinite(x) for x in num['policy_logits']) and -1<=num['value']<=1
            cpcount=cp.get('nn_calls');
            first=q['NN'][0]; pubs=q['sab_publications'];assert pubs
            assert pubs[-1]['sequence']==r['response']['body']['sequence'], 'PUBLIC_CP_SEQUENCE'
            assert cpcount==pubs[-1]['sequence'], 'NN_COUNTS_NOT_BACKUP_COUNTS'
            assert all(math.isfinite(e[1]) and e[1]>=0 for e in cp['root_edges'])
            assert abs(sum(e[1] for e in cp['root_edges'])-1)<1e-4
            roots.append({'pair':pair,'game':gid,'engine':eng,'turn':r['spec']['turn'],
              'key':identity['key'],'history_SHA':hashlib.sha256(json.dumps(identity['history'],sort_keys=True).encode()).hexdigest(),
              'feature_SHA':hashlib.sha256(json.dumps(num['features_bits']).encode()).hexdigest(),
              'logits':num['policy_logits'],'value':num['value'],
              'first_CP_ms':pubs[0]['validation_end_ms']-identity['t0_ms'],
              'first_API_await_ms':first['session_run_end_ms']-first['session_run_start_ms'],
              'NN_started':r['hand_NN'],'accepted_cp_NN':cpcount,
              'accepted_cp_sim':cp.get('simulations'),'public_sequence':r['response']['body']['sequence'],'public_action':cp['action'],
              'legal_priors':{str(e[0]):e[1] for e in cp['root_edges']},
              'parentQ':'unobserved; no edge-average imputation'})
    # Match only first-to-move side across the two colour assignments.
    side=pd['prefixes'][pair-1]['fixture']['player']
    a=next(x for x in roots if x['pair']==pair and x['game']==f'pair{pair}-color{side}' and x['engine']=='candidate')
    b=next(x for x in roots if x['pair']==pair and x['game']==f'pair{pair}-color{3-side}' and x['engine']=='reference')
    assert (a['key'],a['history_SHA'],a['feature_SHA'])==(b['key'],b['history_SHA'],b['feature_SHA'])
    assert a['legal_priors'].keys()==b['legal_priors'].keys()=={str(x) for x in pd['prefixes'][pair-1]['fixture']['legal_ids']}
    matches.append({'pair':pair,'matched_board_side_history_features':True,'legal_actions':len(a['legal_priors']),
      'max_logit_difference':max(abs(x-y)for x,y in zip(a['logits'],b['logits'])),
      'value_difference':abs(a['value']-b['value']),
      'max_prior_difference':max(abs(a['legal_priors'][k]-b['legal_priors'][k]) for k in a['legal_priors']),
      'candidate_reference_CP_NN':[a['accepted_cp_NN'],b['accepted_cp_NN']],
      'candidate_reference_first_CP_ms':[a['first_CP_ms'],b['first_CP_ms']],
      'candidate_reference_first_API_ms':[a['first_API_await_ms'],b['first_API_await_ms']],
      'candidate_reference_actions':[a['public_action'],b['public_action']]})
assert len(roots)==8
for r in roots:del r['logits'];del r['legal_priors']
# Explicit toy model, not fitted to either cohort.
sig=lambda x:1/(1+math.exp(-x))
toy=[{'synthetic_side_logodds':b,'expected_Xi_delta0':.5,
      'expected_Xi_delta0_5':(sig(b+.5)+sig(-b+.5))/2,
      'local_sensitivity_at_equal':sig(b)*(1-sig(b))}for b in [0,3,5]]
result={'issue':'quoridor-4lc.121','run':'saved-pairs-r2','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 '117':old,'119':new,'roots_read':roots,'matched_initial_roots':matches,'synthetic_sensitivity':toy,
 'input_refs_SHA256':refs,'old_new_pooled':False,'NN':0,'game':0,'actual_go':False,
 'limitations':['Independent arithmetic of owner saved values, not new independent browser replay or runtime acceptance.',
 '119 writer final stop/Git/handoff pending at intake; fixed runtime source Git is in pair summary.',
 'Only two same-input engine root matches; no all-state/CPU equality or pureNN timing.',
 'Legal diverse prefixes not calibrated balanced/IID/representative; all8 retained, no retrospective selection.']}
for p,h in refs.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
(OUT/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'old_Xi':old['Xi_mean'],'new_Xi':new['Xi_mean'],'old_same_side':old['same_side_pair_n'],
 'new_same_side':new['same_side_pair_n'],'totals':new['totals'],'matched_roots':matches,'toy':toy},indent=2))
