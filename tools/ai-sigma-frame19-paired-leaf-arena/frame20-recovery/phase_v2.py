"""One saved-output NN0 calculation: paired-recovery-v1, no model/search imports."""
from pathlib import Path
from collections import Counter
import json,hashlib,sys,math,time,datetime,statistics
c=json.load(open(sys.argv[1]));assert c['task']=='frame20-paired-recovery-242-v1'and c['schema']=='paired-recovery-v1';O=Path(c['output']);assert not O.exists();start=time.monotonic();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in c['inputs'].items():assert sha(p)==h,p
D=Path(c['old_data']);plan=json.load(open(D/'openings8-v1.json'));final=json.load(open(D/'all8-final-ledger.json'));ledger=final['ledger'];assert len(ledger)==8 and all(x['status']=='TERMINAL'for x in ledger)
slots={x['slot']:x for x in ledger};rows=[];service=[]
for run in ['family0-r1','family1-r1']:
 result=json.load(open(D/(run+'.json')));process=json.load(open(D/'guardians'/run/'process.json'));assert result['samples']==process['samples_actual']
 for line in open(D/(run+'-hands.jsonl')):
  h=json.loads(line);slot=slots[h['slot']];k=h['clock'];x=k['response'];r=x['search'];assert k['status']=='RECEIVED'and x['type']=='RESULT'
  assert x['id']==h['id']and x['generation']==h['generation'];assert x['key']==r['root_key']and x['history']==r['root_history']
  assert x['leaf_package']is slot['leaf_package']and r['leaf_package']is slot['leaf_package']
  assert x['validation']['valid']and x['validation']['legal']and x['validation']['value_finite']and r['action_legal'];assert math.isfinite(r['value'])
  assert r['completed_depth']>=1 and r['last_completed_only']and r['parent_copy_key_history_restored']
  assert k['elapsed_ms']<=100 and k['received_ms']-k['t0_ms']<=100 and abs((k['received_ms']-k['t0_ms'])-k['elapsed_ms'])<1e-6
  assert r['node_cap']==32768 and r['stats']['processed']<=32768
  completed=[d for d in r['depths']if d['status']=='COMPLETED'];assert completed[-1]['completed_depth']==r['completed_depth']
  assert all(d.get('adopted')is False for d in r['depths']if d['status']=='INCOMPLETE')
  assert h['side']==slot['NNUE_side'] if h['engine']=='NNUE' else h['side']==slot['D_side']
  prefix=slot['prefix'][:h['ply']];prefixSHA=hashlib.sha256(json.dumps(prefix,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  h.update(variant='candidate'if slot['leaf_package']else'baseline',family=slot['family'],NNUE_side=slot['NNUE_side'],prefix_SHA=prefixSHA)
  rows.append(h)
assert len(rows)==sum(x['hands']for x in ledger)==338
metrics=[]
for mode in [False,True]:
 variant='candidate'if mode else'baseline';games=[s for s in ledger if s['leaf_package']==mode]
 for engine in ['NNUE','distance']:
  rr=[h for h in rows if h['variant']==variant and h['engine']==engine];rs=[h['clock']['response']['search']for h in rr];stats=[r['stats']for r in rs];timev=[h['clock']['elapsed_ms']for h in rr]
  metrics.append({'variant':variant,'engine':engine,'planned_games':len(games),'terminal_games':len(games),'NNUE_WDL':dict(Counter(s['result_NNUE']for s in games)),'received_hands':len(rr),'completed_depth_counts':dict(Counter(r['completed_depth']for r in rs)),'completed_depth_mean':statistics.mean(r['completed_depth']for r in rs),'processed_nodes':sum(s['processed']for s in stats),'NN':sum(s['NN']for s in stats),'D_evals':sum(s['D_evals']for s in stats),'nodecap_reached_hands':sum(s['processed']==32768 for s in stats),'nodecap_reached_rate':sum(s['processed']==32768 for s in stats)/len(rr),'typed_stop_counts':dict(Counter(r['typed_stop']for r in rs)),'partial_depth_discarded_hands':sum(r['partial_depth_discarded']is not None for r in rs),'elapsed_mean_ms':statistics.mean(timev),'elapsed_max_ms':max(timev),'clock_slack_min_ms':100-max(timev),'late_count':0,'latevalid_count':0,'whole_search_ms_sum':sum(r['wholewall_ms']for r in rs),'clock_elapsed_ms_sum':sum(timev),'timer_callback_recorded':sum(h['clock']['timer_fired_ms']is not None for h in rr),'scope':'different reached states/workload;aggregate ratios not fixedwork/causal engine benefit'})
matched=[];pair_summaries=[]
for base,cand in [(1,2),(4,3),(5,6),(8,7)]:
 a,b=slots[base],slots[cand];assert a['family']==b['family']and a['NNUE_side']==b['NNUE_side'];op=next(o for o in plan['openings']if o['family']==a['family']);assert a['prefix'][:op['opening_ply']]==b['prefix'][:op['opening_ply']]==op['prefix']
 ar=[h for h in rows if h['slot']==base];br=[h for h in rows if h['slot']==cand]
 amap={};bmap={}
 for dest,hs in [(amap,ar),(bmap,br)]:
  for h in hs:
   key=(h['engine'],h['clock']['response']['key'],h['clock']['response']['history']);assert key not in dest;dest[key]=h
 pair=[]
 for key in amap.keys()&bmap.keys():
  ha,hb=amap[key],bmap[key];ra,rb=[h['clock']['response']['search']for h in [ha,hb]];da={d['completed_depth']:d for d in ra['depths']if d['status']=='COMPLETED'};db={d['completed_depth']:d for d in rb['depths']if d['status']=='COMPLETED'};common=[]
  for depth in sorted(da.keys()&db.keys()):
   aa,bb=da[depth],db[depth];delta=bb['value']-aa['value'];common.append({'depth':depth,'baseline_value':aa['value'],'candidate_value':bb['value'],'maxabs':abs(delta),'value_under_fixed_tol':abs(delta)<=1e-5+1e-4*abs(aa['value']),'baseline_Action':aa['Action'],'candidate_Action':bb['Action'],'Action_equal':aa['Action']==bb['Action'],'equal_argmax_set':'NOT_RECORDED','nonbest_allchild_exact':'NOT_RECORDED'})
  rec={'baseline_slot':base,'candidate_slot':cand,'family':a['family'],'NNUE_side':a['NNUE_side'],'engine':key[0],'input_key':key[1],'history_SHA':hashlib.sha256(key[2].encode()).hexdigest(),'baseline_ply':ha['ply'],'candidate_ply':hb['ply'],'same_exact_prefix':ha['prefix_SHA']==hb['prefix_SHA'],'baseline_completed_depth':ra['completed_depth'],'candidate_completed_depth':rb['completed_depth'],'completed_depth_delta':rb['completed_depth']-ra['completed_depth'],'baseline_processed':ra['stats']['processed'],'candidate_processed':rb['stats']['processed'],'baseline_NN':ra['stats']['NN'],'candidate_NN':rb['stats']['NN'],'baseline_Action':ra['Action'],'candidate_Action':rb['Action'],'final_Action_equal':ra['Action']==rb['Action'],'same_final_completed_depth':ra['completed_depth']==rb['completed_depth'],'baseline_elapsed_ms':ha['clock']['elapsed_ms'],'candidate_elapsed_ms':hb['clock']['elapsed_ms'],'common_completed_depths':common,'scope':'same recorded board+side+RuleA count-history input;search partial/horizon can differ'}
  pair.append(rec);matched.append(rec)
 exactcommon=sum(h['same_exact_prefix']for h in pair);prefix_identical=a['prefix']==b['prefix'];pair_summaries.append({'baseline_slot':base,'candidate_slot':cand,'family':a['family'],'NNUE_side':a['NNUE_side'],'baseline_result':a['result_NNUE'],'candidate_result':b['result_NNUE'],'baseline_hands':a['hands'],'candidate_hands':b['hands'],'starting_prefix_same':True,'all_final_prefix_identical':prefix_identical,'matched_input_hands':len(pair),'same_exact_prefix_matches':exactcommon,'final_Action_disagreements_on_matched_inputs':sum(not x['final_Action_equal']for x in pair),'common_depth_value_checks':sum(len(x['common_completed_depths'])for x in pair),'common_depth_value_faults':sum(not d['value_under_fixed_tol']for x in pair for d in x['common_completed_depths']),'common_depth_Action_differences':sum(not d['Action_equal']for x in pair for d in x['common_completed_depths'])})
match_engine=[]
for engine in ['NNUE','distance']:
 rr=[h for h in matched if h['engine']==engine];ds=[x['completed_depth_delta']for x in rr];match_engine.append({'engine':engine,'same_input_pairs':len(rr),'candidate_deeper':sum(x>0 for x in ds),'same_depth':sum(x==0 for x in ds),'candidate_shallower':sum(x<0 for x in ds),'mean_depth_delta':statistics.mean(ds)if ds else None,'final_Action_changed':sum(not x['final_Action_equal']for x in rr),'common_depth_value_checks':sum(len(x['common_completed_depths'])for x in rr),'common_depth_value_maxabs':max([d['maxabs']for x in rr for d in x['common_completed_depths']]or[0]),'common_depth_Action_diff':sum(not d['Action_equal']for x in rr for d in x['common_completed_depths'])})
procs=[json.load(open(D/'guardians'/r/'process.json'))for r in ['preflight-r1','family0-r1','family1-r1']];bgs=[json.load(open(D/('background-'+r)/'result.json'))for r in ['preflight-r1','family0-r1','family1-r1']]
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':c['task'],'schema':c['schema'],'NN':0,'model':0,'GPU':0,'input_SHA':c['inputs'],'planned8':8,'all_terminal':8,'UNKNOWN':0,'NOT_STARTED':0,'families':2,'color_swaps':True,'per_variant_NNUE_WDL':{'baseline':{'W':2,'D':0,'L':2},'candidate':{'W':2,'D':0,'L':2}},'service_all_adopted_hands':len(rows),'all_clock_t1_le100_mode_id_generation_key_history_legal_saved_validation':True,'legal_verification_scope':'saved acceptance plus immutable arena validation source;no new RuleA replay or independent legality proof','metrics':metrics,'paired_games':pair_summaries,'matched_engine_summaries':match_engine,'matched_inputs':matched,'old_science':{'NN':sum(x['samples_charge']for x in procs),'guardian_wall_s':sum(x['wall_s']for x in procs),'controller_family_wall_ms':sum(json.load(open(D/(r+'.json')))['wholewall_ms']for r in ['family0-r1','family1-r1']),'startup_to_ready_ms':[json.load(open(D/(r+'.json')))['init_to_ready_ms']for r in ['family0-r1','family1-r1']],'background_wall_s':sum(x['wall_seconds']for x in bgs),'control_wait_s':[json.load(open(D/(r+'-wait.json')))['control_wait_s']for r in ['preflight-r1','family0-r1','family1-r1']],'peak_family_RSS_B':max(x['peak_family_RSS']for x in procs),'NNcaps_not_reset':True},'limits':['2family/4paired color positions/8games;not 8independent openings','package applied to bothNNUE andD;relativeWDL cannot isolate absoluteengine improvement','different reached states,32768 bothnodecap,partial depth discarded,TT0/noise0/policy0','sameinput comparisons use recorded board+side+canonical count-history;common completeddepth only;equalargmax unavailable','branchcache/JIT/order/clock sampling;not formalNI or unseen strength','old236/2408192 and differentprefix results not directcausal control','oldscience unchanged/oldopenedtest no read/newforward0','LLMfailed cost UNKNOWN;known sciencewall and background/control spans not additive'],'management_math_wall_s':time.monotonic()-start}
O.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'task':c['task'],'schema':c['schema'],'NN':0,'adoptedhands':len(rows),'matched_pairs':len(matched),'matched_engine_summaries':match_engine,'math_wall_s':time.monotonic()-start}))
