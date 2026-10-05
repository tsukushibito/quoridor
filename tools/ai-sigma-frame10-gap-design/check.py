"""Static design arithmetic; no AI, browser, original checker import, or sampling."""
import hashlib, json, math, pathlib, subprocess, datetime
R = pathlib.Path(__file__).resolve().parents[2]
D = R / 'research-data/ai-sigma/frame10-gap-design'
sha = lambda b: hashlib.sha256(b).hexdigest()
refs = []
def read(p, git=None):
    b = (R/p).read_bytes()
    git = git or subprocess.check_output(['git','log','-1','--format=%H','--',p], text=True).strip()
    if not git: raise ValueError('unbound source '+p)
    assert b == subprocess.check_output(['git','show',git+':'+p]), p
    refs.append(dict(path=p, Git=git, SHA256=sha(b), bytes=len(b)))
    return json.loads(b) if p.endswith('.json') else b.decode()
read('docs/design/ai-sigma-contract-critic-frame10-gap-design.md', '40243b25804f8e929a6af5680c02a2b70bef39d1')
read('docs/design/ai-sigma-contract-experiment-frame10-baseline-gap.md', '40243b25804f8e929a6af5680c02a2b70bef39d1')
old = read('research-data/ai-sigma/119-diverse-prefix/final-results.json')
reg = read('research-data/ai-sigma/119-diverse-prefix/preregister.json')
proposal = read('research-data/ai-sigma/145-matched-policy-quality-choice/proposal.json')
read('docs/design/ai-sigma-frame8-evaluation-plan.md')
read('research-data/ai-sigma/116-evaluation-plan/arithmetic.json')
games = old['games'] if 'games' in old else old['rows']
pairs = {}
score = {'W':1.0, 'D':.5, 'L':0.0}
for g in games:
    k = g['fixture_id']; c = g['candidate_color']
    assert g['status']=='terminal' and g['reason']=='goal' and c in [1,2]
    s = 1.0 if g['winner']==c else 0.0
    assert score[g['candidate_result']]==s
    assert c not in pairs.setdefault(k,{})
    pairs[k][c]=s
assert len(pairs)==8 and all(set(v)=={1,2} for v in pairs.values())
xis = [(v[1]+v[2])/2 for v in pairs.values()]
assert sum(xis)/8 == .25 and sum(g['candidate_result']=='W' for g in games)==4
assert len(proposal['inputs']['prefixes'])==3 and proposal['denominators']['planned_games']==12
def planned_bounds(slots):
    # Each color score has weight 1/64; unknown is an interval, never zero imputed.
    assert len(slots)==64
    lo = sum(0 if x is None else x for x in slots)/64
    hi = sum(1 if x is None else x for x in slots)/64
    return [lo, hi]
assert planned_bounds([None]*64)==[0,1]
assert planned_bounds([1]*32+[None]*32)==[.5,1]
assert planned_bounds([0,1]*32)==[.5,.5]
assert planned_bounds([0]*32+[None]*32)==[0,.5]
radius = {str(n): math.sqrt(math.log(2/.05)/(2*n)) for n in [8,16,32,64]}
weights = [1/4/8]*32
assert abs(sum(weights)-1)<1e-12 and abs(sum(w*w for w in weights)-1/32)<1e-12
two_sided_required_05 = math.ceil(math.log(2/.05)/(2*.05**2))
plies = [4,5,12,13]
nominal_think = sum((200-p)*.5*16 for p in plies)
result = dict(issue='quoridor-4lc.147', UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    refs=refs, old119=dict(pair_units=8, games=16, Xi=xis, mean=.25, W=4, L=12,
        inference_as_current_weakness=False, incorporated_into_new_result=False,
        generator=reg['generation_rule'], accepted_CP_NN_medians={e:old['engines'][e]['completed_cp_NN_distribution']['median'] for e in ['candidate','reference']},
        APIawait_is_CPU=False),
    old145=dict(proposal_only=True, prefixes=proposal['inputs']['prefixes'], independent_positions=3, games=12, seeds_not_new_positions=True),
    precision=dict(alpha=.05, method='two-sided bounded-pair Hoeffding', radius=radius,
        n_for_radius_le_05=two_sided_required_05, independent_bounded_units_required=True,
        IID_not_required_for_fixed_equal_stratum_weight_bound=True,
        PRNG_seed_or_temporal_independence_not_proved=True, weights=weights,
        no_actual_CI_or_power_certification=True),
    missing_examples=dict(all_unknown=planned_bounds([None]*64), half_wins_unknown=planned_bounds([1]*32+[None]*32), half_losses_unknown=planned_bounds([0]*32+[None]*32)),
    cost=dict(planned_pair=32, planned_game=64, prefix_lengths=plies, nominal_think_all_max_200ply_s=nominal_think,
        browser_cap_s=7200, residual_budget_s=7200-nominal_think,
        nominal_not_measured_wall=True, startup_calls_if_six_per_fresh_game=384,
        equal_completed_additional_games=0),
    attempts=dict(static=1, NN=0, Chrome=0, model=0, game=0, build=0), failures=[])
(D/'arithmetic.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['old119','precision','missing_examples','cost']}))
