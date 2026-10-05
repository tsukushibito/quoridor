"""241 dedicated saved arithmetic. No imports of model, NN, Torch, or old checker."""
import argparse,collections,datetime,hashlib,json,math,pathlib,subprocess,time
ap=argparse.ArgumentParser();ap.add_argument('--task',required=True);ap.add_argument('--input-manifest',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();assert a.task=='frame19-leaf-terminal-241-v1';begin=time.monotonic();D=pathlib.Path(__file__).parent;P=pathlib.Path('research-data/ai-sigma/frame19-leaf-terminal');sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(pathlib.Path(p).read_text());inp=load(a.input_manifest)
for p,h in inp['SHA'].items():assert sha(p)==h,('changed',p)
fixture=load(P/'fixture-result-r2.json');fc=fixture['checks'];assert len(fc)==64 and len({x['id']for x in fc})==64
terms=[];non=[]
for x in fc:
 assert x['parent_key_history_unchanged']
 if x['terminal']is None:
  assert x['D_f32_bitexact']and x['NNUE_same_input_bitexact']and x['parent_buffer_unchanged'];non.append(x)
 else:
  assert x['terminal']['winner']in[0,1,2]and x['terminal']['value']in[-1,0,1];terms.append(x)
assert fixture['samples']==2*len(non)
byid={x['id']:x for x in fc};assert byid['synthetic-history-no-pawn-wall-fallback']['terminal']is None and byid['synthetic-history-no-pawn-wall-fallback']['stats']['leaf_full_fallback']==1;assert byid['synthetic-history-no-pawn-no-wall-draw']['terminal']=={'winner':0,'value':0};assert byid['draw-200']['terminal']=={'winner':0,'value':0}
profile=load(P/'profile-result-r2.json');rs=profile['results'];assert len(rs)==64;groups=collections.defaultdict(list);tot=collections.defaultdict(lambda:collections.defaultdict(float));rounds=collections.defaultdict(lambda:collections.defaultdict(float));engine_round=collections.defaultdict(lambda:collections.defaultdict(float));matches=0
for x in rs:
 assert x['status']=='COMPLETED_ACTION'and x['requested_depth']==3 and x['node_cap']==8192 and x['last_completed_only']and x['action_legal']and x['parent_copy_key_history_restored'];assert x['stats']['visited']==x['stats']['processed']+x['stats']['rejected_entry'];assert not x['policy_exclusion']and x['TT']==0 and x['noise']==0
 groups[(x['round'],x['root'],x['engine'])].append(x);key=x['engine']+'/'+x['variant'];tot[key]['searches']+=1;tot[key]['wholewall_ms']+=x['wholewall_ms'];rounds[x['round']][x['variant']]+=x['wholewall_ms'];engine_round[(x['round'],x['engine'])][x['variant']]+=x['wholewall_ms']
 for k in ['processed','NN','leaf_checks','leaf_pawn_fast_nonterminal','leaf_full_fallback','leaf_winner','leaf_draw200','internal_full_terminal']:tot[key][k]+=x['stats'].get(k,0)
 for dep in x['depths']:
  if dep['status']=='INCOMPLETE':assert dep['adopted']is False
assert len(groups)==16
for key,xs in groups.items():
 xs.sort(key=lambda x:x['order']);assert [x['order']for x in xs]==[0,1,2,3]and [x['variant']for x in xs]==['baseline','candidate','candidate','baseline'];base=xs[0]
 for x in xs[1:]:
  assert x['stats']['processed']==base['stats']['processed']and x['stats']['NN']==base['stats']['NN'];assert x['completed_depth']==base['completed_depth'];bc={d['completed_depth']:d for d in base['depths']if d['status']=='COMPLETED'};xc={d['completed_depth']:d for d in x['depths']if d['status']=='COMPLETED'};assert set(bc)==set(xc)
  for depth,b in bc.items():
   c=xc[depth];assert b['Action']==c['Action']and abs(b['value']-c['value'])<=1e-5+1e-4*abs(b['value']);assert b['root_all_legal_count']==c['root_all_legal_count']
  matches+=1
assert matches==48 and profile['samples']==fixture['samples']+sum(x['stats']['NN']for x in rs)
summary={}
for engine in ['NNUE','distance']:
 b=tot[engine+'/baseline'];c=tot[engine+'/candidate'];summary[engine]={'baseline':dict(b),'candidate':dict(c),'wall_reduction':1-c['wholewall_ms']/b['wholewall_ms'],'rate_ratio':b['wholewall_ms']/c['wholewall_ms'],'round_reductions':{str(r):1-z['candidate']/z['baseline']for(r,e),z in engine_round.items()if e==engine}}
all_b=sum(x['wholewall_ms']for x in rs if x['variant']=='baseline');all_c=sum(x['wholewall_ms']for x in rs if x['variant']=='candidate');profilecalc={'searches64':True,'matches48':matches,'same_last_completed_depth':True,'same_all_completed_depths':True,'total_baseline_ms':all_b,'total_candidate_ms':all_c,'total_reduction':1-all_c/all_b,'round_reductions':{str(r):1-z['candidate']/z['baseline']for r,z in rounds.items()},'by_engine':summary,'NN_including_fixture':profile['samples'],'fast_count':sum(x['stats'].get('leaf_pawn_fast_nonterminal',0)for x in rs),'fallback_count':sum(x['stats'].get('leaf_full_fallback',0)for x in rs),'spans_not_exclusive':True}
processes=[load(p)for p in sorted((P/'guardians').glob('*/process.json'))];assert len(processes)==5
for p in processes:assert p['all_child_waited']and p['current_exact_absent']and not p['remaining']
known=sum(p['samples_actual']for p in processes if isinstance(p['samples_actual'],int));charge=sum(p['samples_charge']for p in processes);wall=sum(p['wall_s']for p in processes);unknown=[{'startUTC':p['startUTC'],'actual':p['samples_actual'],'conservative':p['samples_charge'],'inflight':p['inflight_NN_unknown']}for p in processes if p.get('inflight_NN_unknown')or p['samples_actual']is None]
assert known==fixture['samples']+sum(x['stats']['NN']for x in rs)+load(P/'optional4-r1-censored-ledger.json')['known_NN']+load(P/'remaining3-r1.json')['samples']+load(P/'exact-cases-r1.json')['samples'];assert charge-known==550000+8192
manifest=load(P/'openings4-v1.json');old=load(P/'optional4-r1-censored-ledger.json');rem=load(P/'remaining3-r1.json');assert len(manifest['slots'])==4 and len({x['family']for x in manifest['slots']})==2;assert old['ledger'][0]['status']=='UNKNOWN'and old['ledger'][0]['hands']==19 and not old['normal_loss'];ledger=[old['ledger'][0]]+[x for x in rem['ledger']if x['slot']in[2,3,4]];assert sorted(x['slot']for x in ledger)==[1,2,3,4];W=collections.Counter({'UNKNOWN':1});clockstats=collections.Counter();late=[];hands=[]
for n in ['optional4-r1-hands.jsonl','remaining3-r1-hands.jsonl']:
 for line in (P/n).read_text().splitlines():
  h=json.loads(line);hands.append(h);cl=h['clock'];assert cl['budget_ms']==100 and abs(cl['received_ms']-cl['t0_ms']-cl['elapsed_ms'])<1e-6;r=cl.get('response');clockstats['recorded']+=1
  if r and r['type']=='RESULT':clockstats['service_RESULT']+=1;assert r['id']==h['id']and r['generation']==h['generation']
  if cl['status']!='RECEIVED':late.append({'slot':h['slot'],'ply':h['ply'],'status':cl['status'],'elapsed_ms':cl['elapsed_ms'],'valid':r.get('validation',{}).get('valid')if r else None,'completed_depth':r.get('search',{}).get('completed_depth')if r else None});continue
  assert cl['elapsed_ms']<=100 and r['validation']['valid'];s=r['search'];assert s['completed_depth']>=1 and s['last_completed_only']and s['action_legal'];assert r['key']==s['root_key']and r['history']==s['root_history'];clockstats['adopted']+=1
  for d in s['depths']:
   if d['status']=='INCOMPLETE':assert not d['adopted']
for g in ledger[1:]:assert g['status']=='TERMINAL';derived='W'if g['winner']==g['NNUE_side']else'D'if g['winner']==0 else'L';assert derived==g['result_NNUE'];W[derived]+=1
assert len([h for h in hands if h['slot']==1])==19
exact=load(P/'exact-cases-r1.json');pr=load(P/'exact-cases-preregister-v1.json');assert sha(pr['source'])==pr['sourceSHA'];selected=load(pr['source'])['cases'];assert pr['cases']==selected and len(selected)==4;ers=exact['results'];assert len(ers)==16;casechecks=[]
for x in ers:
 f=selected[x['caseIndex']];assert (x['slot'],x['ply'],x['source_hand_id'],x['source_selected_Action'])==(f['slot'],f['ply'],f['source_hand_id'],f['Action']);assert x['engine']in['NNUE','distance']and x['depth']in[1,2]
 if x['status']!='COMPLETED':casechecks.append({'case':x['caseIndex'],'engine':x['engine'],'depth':x['depth'],'typed':'INCOMPLETE','stop':x.get('typed_stop')});continue
 v=x['values'];assert len(v)==x['legal_count']and len({z['Action']for z in v})==len(v);assert all(math.isfinite(z['value'])and z['bound']=='EXACT_FINITE_DEPTH_FULL_WINDOW'for z in v);maximum=max(z['value']for z in v);ties=[z['Action']for z in v if z['value']==maximum];sv=next(z['value']for z in v if z['Action']==f['Action']);assert maximum==x['max_value']and ties==x['argmax_Actions']and ties[0]==x['strict_first_Action']and sv==x['source_selected_value']and abs(maximum-sv-x['source_selected_gap'])<1e-12
 same_source=(x['engine']=='NNUE'and x['depth']==f['completed_depth']);value_diff=sv-f['value']if same_source else None
 if same_source:assert abs(value_diff)<=1e-5+1e-4*abs(f['value'])
 casechecks.append({'case':x['caseIndex'],'reason':f['reason'],'engine':x['engine'],'depth':x['depth'],'legal_count':len(v),'maximum':maximum,'argmax_Actions':ties,'source_Action':f['Action'],'source_selected_value':sv,'source_gap':maximum-sv,'source_same_depth_value_difference':value_diff,'parent_receipt_only':x['parent_copy_key_history_buffer_restored']})
assert len({(x['caseIndex'],x['engine'],x['depth'])for x in ers})==16;assert sum(x['stats']['NN']for x in ers)==exact['samples']and sum(x['stats']['processed']for x in ers)==exact['processed']
childcmd=['node','--max-old-space-size=384',str(D/'replay-leaf.cjs'),'--task','frame19-leaf-replay-241-v1','--input-manifest',a.input_manifest,'--out',str(D/'replay-result.json')];cp=subprocess.Popen(childcmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);stat=pathlib.Path('/proc',str(cp.pid),'stat').read_text().rsplit(')',1)[1].split();tick=stat[19];stdout,stderr=cp.communicate(timeout=35);assert cp.returncode==0,stderr.decode();ps=pathlib.Path('/proc',str(cp.pid),'stat');absent=not ps.exists()or ps.read_text().rsplit(')',1)[1].split()[19]!=tick;assert absent;replay=load(D/'replay-result.json');assert replay['schema']=='leaf-terminal-replay-v1'and replay['task']=='frame19-leaf-replay-241-v1'and replay['PASS']
result={'schema':'leaf-terminal-independent-v1','task':a.task,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PASS':True,'newNN':0,'fixture_receipts':{'all64':len(fc),'nonterminal_D_NN_input_receipts':len(non),'terminal':len(terms),'numeric_receipt_owner_only_not_re_forward':True,'synthetic_fallback_guard':True},'profile':profilecalc,'allattempt':{'knownNN':known,'conservativeNN':charge,'guardian_wall_s':wall,'unknown_attempts':unknown,'attempts':len(processes),'no_overlap_addition':True},'optional':{'planned4':4,'families2':2,'WDL':dict(W),'clock_counts':dict(clockstats),'late_nonadopted':late,'unrecorded_inflight_UNKNOWN':True,'slot1_not_restarted':True},'exact_cases':{'conditions':len(ers),'completed':sum(x['status']=='COMPLETED'for x in ers),'NN':exact['samples'],'processed':exact['processed'],'rows':casechecks,'value_truth_receipt_only':True,'old_nonbest_failsoft_not_exact':True},'rule_replay':replay,'child_process':{'PID':cp.pid,'tick':tick,'exit':cp.returncode,'wait':True,'current_exact_absent':absent},'limits':['shared RuleA, finite saved numeric receipts, no model reload/forward','small fixed roots and paired opening families, no general strength/NI','package includes D redundantterminal removal, not unique operator cause','239 selected exploratory cases, not unseen test or exact game truth'],'wall_s':time.monotonic()-begin}
for p,h in inp['SHA'].items():assert sha(p)==h,('changed after',p)
pathlib.Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['PASS','profile','allattempt','optional','exact_cases','child_process','wall_s']}))
