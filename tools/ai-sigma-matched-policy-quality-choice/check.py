import pathlib,json,hashlib,itertools,time,datetime,os,resource
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/145-matched-policy-quality-choice';start=datetime.datetime.now(datetime.timezone.utc).isoformat();inputs={}
def read(path):
 p=R/path;raw=p.read_bytes();inputs[path]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
preg=read('research-data/ai-sigma/119-diverse-prefix/preregister.json');pairs=[x for x in preg['pairs'] if x['pair'] in [1,7,8]]
summary=[]
for x in pairs:
 s=read(f"research-data/ai-sigma/119-diverse-prefix/prefix119-pair{x['pair']}-r1.summary.json")
 summary.append({'pair':x['pair'],'prefix_ply':x['prefix_ply'],'old_results':[g['candidate_result'] for g in s['games']],'old_public':sum(g['legal_actions_saved'] for g in s['games']),'old_terminal_total_ply':[g['total_ply'] for g in s['games']]})
# Max RuleA depth200 includes the already completed prefix; four future games/prefix.
plies=sum(4*(200-x['prefix_ply']) for x in pairs);think=plies*.5
order=[]
for j,x in enumerate(pairs):
 for color in [1,2]:
  variants=['A','B'] if (j+color)%2==1 else ['B','A']
  order.append({'cell':len(order)+1,'prefix':x['pair'],'candidate_color':color,'order':variants,'same_search_seed':2098,'games':[{'variant':v,'C':1.5 if v=='A' else 1.0,'prefix':x['pair'],'candidate_color':color,'seed':2098} for v in variants],'session_cap_s':250})
assert len(order)==6 and sum(len(x['games']) for x in order)==12 and sum(x['order']==['A','B'] for x in order)==3
assert plies==2252 and think==1126 and sum(x['session_cap_s'] for x in order)==1500
baseline=R/'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm';c1=R/'research-data/ai-sigma/110-c-factor-browser/binaries/c1.wasm';manifest=read('research-data/ai-sigma/110-c-factor-browser/build-manifest.json');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(baseline)==manifest['original_Wasm_SHA'];assert sha(c1)==manifest['C1_Wasm_SHA'];inputs[str(baseline.relative_to(R))]=sha(baseline);inputs[str(c1.relative_to(R))]=sha(c1)
source=R/'crates/quoridor-ai/src/lib.rs';src=source.read_text();inputs[str(source.relative_to(R))]=sha(source);assert 'const PUCT_C: f32 = 1.5;' in src and 'q + PUCT_C * edge.prior * root / (edge.visits + 1) as f32' in src
worker=R/'tools/ai-sigma-player-workers/player-main.js';ws=worker.read_text();inputs[str(worker.relative_to(R))]=sha(worker);assert 'seed:1979' in ws
read('research-data/ai-sigma/144-wallless-ai-sensitivity/handoff-summary.json');early=read('.artifacts/ai-sigma/resume-20261002/coordinator144-early-stop-check.json');read('.artifacts/ai-sigma/resume-20261002/coordinator143-heavy-stop-check.json')
def decision(cells,fault=False):
 if fault or any(x is None for x in cells):return 'incomplete-or-fault-no-policy-change'
 delta=[(cells[i]+cells[i+1])/2 for i in range(0,6,2)];pos=sum(x>0 for x in delta);neg=sum(x<0 for x in delta)
 if pos and neg:return 'mixed-end-this-uniform-change-branch'
 if pos>=2:return 'positive-prioritize-new-input-validation-not-adopt'
 if neg>=2:return 'negative-end-C1-on-this-setting-not-universal'
 if not pos and not neg:return 'score-unchanged-end-this-set-no-effect-unproven'
 return 'one-prefix-only-insufficient-end-this-set'
assert decision([0]*6).startswith('score-unchanged')
assert decision([1,1,1,0,0,0]).startswith('positive')
assert decision([-1,-1,-1,0,0,0]).startswith('negative')
assert decision([1,1,-1,-1,0,0]).startswith('mixed')
assert decision([None]*6).startswith('incomplete') and decision([1]*6,True).startswith('incomplete')
counts={}
for v in itertools.product([-1,-.5,0,.5,1],repeat=6):
 k=decision(v);counts[k]=counts.get(k,0)+1
 assert all(-1<=(v[i]+v[i+1])/2<=1 for i in range(0,6,2))
results={'issue':'quoridor-4lc.145','raw_root_selection':[],'new_root_read':0,'selected_old_summary_only':summary,'planned_order':order,'arithmetic':{'planned_games':12,'matched_same_input_color_cells':6,'prefix_units':3,'color_pair_per_variant':3,'global_RuleA_max_depth':200,'max_new_public_plies':plies,'nominal_500ms_think_seconds':think,'six_job_cap_seconds':1500,'nonthink_and_wait_headroom_seconds':1500-think,'startup_NN_per_fresh_twoWorker_game':6,'startup_NN_total_if_each_game_fresh':72,'model_sessions_total':24,'sessions_live_max':2,'build_required':False,'build_fallback_ceiling_seconds':120,'startup_wait_headroom_not_completion_guarantee':True},'binary_reuse':{'A_sha256':sha(baseline),'B_sha256':sha(c1),'baseline_current_equals_110_baseline':True,'110_source':'0f0597e73e5444c2a576121242a02e18417aad01','sole_policy_factor':'PUCT_C1.5->1.0','new_source_build_not_executed':True},'seed_source_pitfall':'player-main limits/game records hardcode1979; new private adapter must deliver and record2098 for both engines, not only edit config/diagnose gate','artificial_decision_fixture_cases':counts,'decision_vectors_checked':5**6,'newNN':0,'newChrome':0,'144_status':'final handoff available during static read; owner6win not independently rescored here; early and final separated','inputs':inputs,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'self_pid':os.getpid(),'self_starttick':int(pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),'affinity':list(os.sched_getaffinity(0)),'ru_maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
assert results['affinity']==[0] and results['ru_maxrss_bytes']<469762048
(D/'static-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({k:results[k] for k in ['arithmetic','decision_vectors_checked','ru_maxrss_bytes']}))
