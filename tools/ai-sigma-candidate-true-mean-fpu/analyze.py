from pathlib import Path
import json,math,struct,datetime,hashlib
T=Path(__file__).parent;R=T.parents[1];D=R/'research-data/ai-sigma/140-candidate-true-mean-fpu';O=R/'.artifacts/ai-sigma/resume-20261002/CANDIDATE-TRUE-MEAN-FPU';B=O/'runs/fpu140-mechanism-r1';d=json.loads((B/'browser-result.json').read_text());rows=d['mean_results']
f32=lambda v:struct.unpack('f',struct.pack('f',v))[0]
assert len(rows)==6 and not d['errors'] and len(d['parity'])==2 and d['branch']=='known_adverse_input3_end'
all_select=[];summary=[]
for row in rows:
 cp=row['cp'];assert cp['simulations']==row['rootN']==32 and row['edge_sum']==31 and row['NN_calls']==32
 rootSel=[];rootMean=None;trueSum=None;allchecks=0
 if row['trace']:
  t=row['trace'];rootSel=[s for s in t['selections'] if s['node_index']==0];assert len(rootSel)==31
  for s in t['selections']:
   events=[e for e in t['visits'] if e['node_index']==s['node_index'] and e['sim_completed_before']<s['sim_completed_before']]
   assert len(events)==s['nodeN'] and s['node_value_sum']==events[-1]['postSum']
   assert f32(s['true_mean'])==f32(f32(s['node_value_sum'])/s['nodeN'])
   allchecks+=1
   if s['node_index']==0:
    edges=row['CPs'][s['sim_completed_before']-1]['cp']['root_edges'];mass=0.
    for e in edges:
     if e[2]>0:mass=f32(mass+f32(e[1]))
    assert f32(s['visited_original_prior_sum'])==mass
    edge=next(e for e in edges if e[0]==s['Action']);assert s['edge_visits']==edge[2] and s['edge_value_sum']==edge[3] and s['prior']==edge[1]
   assert math.isfinite(s['actual_score']) and s['nodeN']>0
  root=cp['tree'][0];trueSum=root['true_value_sum'];rootMean=f32(f32(trueSum)/root['visits'])
  all_select.append({'input':row['fixture_id'],'variant':row['variant'],'all_actual_select_prior_mean_ledger_checked':allchecks})
 spans=row['spans'];apis=[s['API_end_ms']-s['API_start_ms'] for s in spans];ps=[e[2]/31 for e in cp['root_edges'] if e[2]]
 summary.append({'fixture_id':row['fixture_id'],'variant':row['variant'],'Action':cp['action'],'rootN':32,'edge_visits':31,'completed_backups':32,'NN_started_completed':32,'terminal_noNN':0,'discard':0,'max_depth':cp['max_depth'],'node_count':cp['nodes_count'],'edge_count':cp['edges_count'],'cap':cp['cap'],'root_entropy_nats':-sum(p*math.log(p) for p in ps),'root_actual_value_sum':trueSum,'root_actual_mean':rootMean,'original_true_mean_missing':row['variant']=='original','root_unique_visited_actions':sum(e[2]>0 for e in cp['root_edges']),'root_unvisited_selections':sum(not s['visited'] for s in rootSel) if rootSel else None,'all_selects':len(row['trace']['selections']) if row['trace'] else None,'root_fpu_min':min(s['fpu'] for s in rootSel) if rootSel else None,'root_fpu_max':max(s['fpu'] for s in rootSel) if rootSel else None,'first_API_await_ms':apis[0],'total_API_await_ms':sum(apis),'wholewrapper_ms':row['wrapper_end_ms']-row['wrapper_start_ms'],'input_prepare_ms':row['wrapper_start_ms']-row['prepare_start_ms'],'stop_free_ms':row['wrapper_end_ms']-row['stop_start_ms'],'first_CP_elapsed_ms':row['first_CP_ms']-row['wrapper_start_ms'],'kernel_CPU_missing':True})
first=[];shared=[]
for fixture_id in dict.fromkeys(r['fixture_id'] for r in rows):
 q=next(r for r in rows if r['fixture_id']==fixture_id and r['variant']=='q0');f=next(r for r in rows if r['fixture_id']==fixture_id and r['variant']=='fpu')
 for k in range(1,32):
  a=next(s for s in q['trace']['selections'] if s['node_index']==0 and s['sim_completed_before']==k);b=next(s for s in f['trace']['selections'] if s['node_index']==0 and s['sim_completed_before']==k)
  if a['Action']!=b['Action']:
   first.append({'fixture_id':fixture_id,'completed_before':k,'Q0':a,'FPU':b,'same_parent_mean_and_visited_prior':a['true_mean']==b['true_mean'] and a['visited_original_prior_sum']==b['visited_original_prior_sum']});break
 def identity(n):return (n['key'],n['ply'],tuple(sorted((str(k),v) for k,v in n['history'])))
 pairs=[]
 for a in q['trace']['nodes']:
  b=next((n for n in f['trace']['nodes'] if identity(a)==identity(n)),None)
  if b is None:continue
  assert a['features_bits']==b['features_bits'] and a['turn']==b['turn'] and a['terminal']==b['terminal']
  na=a['numeric'];nb=b['numeric'];numeric_exact=na is not None and nb is not None and na['policy_logits']==nb['policy_logits'] and na['value']==nb['value']
  if na is not None and nb is not None:assert numeric_exact
  pairs.append({'key':a['key'],'history_exact':True,'features_exact':True,'turn_terminal_exact':True,'numeric_exact':numeric_exact,'numeric_missing':na is None or nb is None})
 shared.append({'fixture_id':fixture_id,'selected_Q0':8,'selected_FPU':8,'matched_nodes':len(pairs),'pairs':pairs,'general_deep_equality_unrecognized':True})
processes=[json.loads(p.read_text()) for p in (O/'runs').glob('*.process.json')];usage={k:sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in processes if p['phase']==k) for k in ['build','mechanism','quality','protocol']}
oldbinding={n:(R/'tools/ai-sigma-deep-node-comparison/baseline/src'/n).read_bytes()==(R/'tools/ai-sigma-ort-search/src'/n).read_bytes() for n in ['kernel.rs','lib.rs','research.rs']};assert all(oldbinding.values())
a={'issue':'quoridor-4lc.140','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'measured_Git':json.loads((O/'runs/fpu140-mechanism-r1.inputs.json').read_text())['git_commit'],'mechanism_requests_planned_started_completed':[6,6,6],'hand_NN':192,'terminal_noNN':0,'startup_NN':6,'model_sessions':2,'original_Q0_parity':d['parity'],'numeric_gates_all6':True,'actual_ledger_select_checks':all_select,'rows':summary,'comparisons':d['comparisons'],'first_root_selection_divergence':first,'bounded_shared_node_check':shared,'quality_branch':d['branch'],'quality_rollouts_started':0,'quality_permitted_maximum':8,'quality_not_started_reason':'predeclared global input3->133 adverse exit; input4new118 does not override this rule','incomplete_searches':0,'scientific_repeat':0,'known_134_quality_not_new_score':'input3 original161 [1,1], fixedSigma133 [0,0]; finite policy-dependent previousdiagnosis only','current_policy':'maintain Q0/C1.5','FPU_policy_adopted':False,'next_proposal':{'max_one':'separate finite midgame value/longer-horizon input scale feasibility design, NN0 first','cost_estimate':'future allocation only CPU0single <=120sec/RAM1GiB, no automaticNN/model/rollout','falsifier':'if no nontrivial reproducible finite label or value comparison separates legal alternatives within bounded savedinput, stop beforeNN','next_decision':'allocate new evaluation-scale contrast only if discriminatory input/label exists; no sameFPUtwo-state repeats'},'resources':{'managed_seconds':usage,'build_browser_total':sum(usage[k] for k in ['build','mechanism','quality']),'max_current_RSS':max(p['peak_group_plus_runner_RSS'] for p in processes),'original_baseline_current_source_equal':oldbinding,'original_source_binary_binding':'132savedofflinebuildbyteequal pluscurrentimmutablehash; no neworiginalrebuild/independentfullproof','unmanaged_short_management_PID_RSS_fullperiod_affinity_missing':True},'limits':['sameK not sameNN/CPU/wall in general; sameNN32 here observed','APIawait not kernelCPU; tracecostnotfree','realterminalnoNN0 inthese6; artificialterminalfixturesonly','no fixedgolden midgame','postselected2lost-lineinputs notIID/representative/holdout','originalcandidate meanabsent; no edge-average/rootNN supplementation','shared first8node matches not all deep equality','known133 earlyexit notnewqualitygeneralproof/119cause','normal500ms candidateperformance/NI/Sigma/policyadoption unrecognized']}
(D/'analysis.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'branch':a['quality_branch'],'select_checks':sum(r['all_actual_select_prior_mean_ledger_checked'] for r in all_select),'resource_seconds':usage,'shared_nodes':[r['matched_nodes'] for r in shared]}))
