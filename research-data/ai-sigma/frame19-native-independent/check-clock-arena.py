"""238 dedicated saved-clock arithmetic; no inference or old data checker."""
import argparse,collections,datetime,hashlib,json,math,pathlib,statistics,time,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--task',required=True);ap.add_argument('--input-manifest',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();assert a.task=='frame19-clock-arena-238-v1';t=time.monotonic();P=pathlib.Path('research-data/ai-sigma/frame19-native-arena');sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();load=lambda n:json.loads((P/n).read_text());manifest=json.loads(pathlib.Path(a.input_manifest).read_text())
for p,h in manifest['SHA'].items():assert sha(p)==h,(p,'changed')
allr=load('all-attempt-result-v1.json');op=load('openings8-v1.json');ledger=allr['ledger'];assert len(ledger)==8 and sorted(x['slot']for x in ledger)==list(range(1,9));assert len({x['family']for x in ledger})==4
W=collections.Counter();rows=[];slot_rows=collections.defaultdict(list)
for n in ['pilot-r2-hands.jsonl','later4-r1-hands.jsonl']:
 for line in (P/n).read_text().splitlines():
  x=json.loads(line);x['_file']=n;rows.append(x);slot_rows[x['slot']].append(x)
eng=collections.defaultdict(list);fault=[];depths=collections.defaultdict(collections.Counter);stops=collections.defaultdict(collections.Counter);spans=collections.defaultdict(lambda:collections.defaultdict(float));nnreply=0
for x in rows:
 c=x['clock'];assert c['budget_ms']==100 and c['margin_ms']==10;assert abs(c['received_ms']-c['t0_ms']-c['elapsed_ms'])<1e-6
 r=c.get('response');
 if c['status']!='RECEIVED':fault.append({'slot':x['slot'],'ply':x['ply'],'engine':x['engine'],'status':c['status'],'elapsed_ms':c['elapsed_ms'],'response_present':r is not None});continue
 assert c['elapsed_ms']<=100 and r['type']=='RESULT' and r['id']==x['id'] and r['generation']==x['generation'];s=r['search'];assert r['key']==s['root_key']and r['history']==s['root_history'];assert r['validation']['valid']and r['validation']['legal']and r['validation']['value_finite'];assert s['status']=='COMPLETED_ACTION'and s['completed_depth']>=1 and math.isfinite(s['value'])and s['action_legal']and s['last_completed_only']and s['parent_copy_key_history_restored'];assert s['TT']==0 and s['noise']==0 and not s['policy_exclusion']
 completed=[d for d in s['depths']if d['status']=='COMPLETED'];assert completed and completed[-1]['completed_depth']==s['completed_depth']and completed[-1]['Action']==s['Action']
 for d in s['depths']:
  if d['status']=='INCOMPLETE':assert d['adopted']is False
 st=s['stats'];assert st['processed']<=8192 and st['visited']==st['processed']+st['rejected_entry'];nnreply+=st['NN'];eng[x['engine']].append(x);depths[x['engine']][str(s['completed_depth'])]+=1;stops[x['engine']][s['typed_stop']]+=1
 for k,v in s['spans'].items():spans[x['engine']][k]+=v
for x in ledger:
 rr=slot_rows[x['slot']];assert len(rr)==x['hands'];assert x['family']==next(z for z in op['slots']if z['slot']==x['slot'])['family'];status=x['status'];
 if status=='UNKNOWN':assert len([r for r in rr if r['clock']['status']!='RECEIVED'])==1
 else:
  assert status=='TERMINAL';derived=('W'if x['winner']==x['NNUE_side']else'D'if x['winner']==0 else'L');assert x['result_NNUE']==derived;status=derived;assert all(r['clock']['status']=='RECEIVED'for r in rr)
 W[status]+=1
assert dict(W)=={k:v for k,v in allr['WDL_NNUE'].items()if v};assert len(rows)==297 and len(fault)==1 and fault[0]['slot']==1
procs=allr['processes'];assert len(procs)==4 and all(q['all_child_waited']and q['current_exact_absent']and not q['remaining']for q in procs);known=sum(q['samples_actual']for q in procs);charge=sum(q['conservative_charge_with_supplement']for q in procs);wall=sum(q['wall_s']for q in procs);assert known==270156==allr['physical_NN_known']and charge==278348==allr['NN_conservative_charge'];assert abs(wall-allr['guardian_science_all_attempt_wall_s'])<1e-10
bench=load('bench-r1.json');assert len(bench['results'])==32 and sum(x['stats']['NN']for x in bench['results'])==bench['samples']==60880
benchsummary=[{k:x[k]for k in ['rep','root','engine','ordering','completed_depth','Action','wholewall_ms']}for x in bench['results']]
initial=[x for x in benchsummary if x['root']=='initial-p1'and x['engine']=='NNUE'];assert [(x['ordering'],x['completed_depth'])for x in initial]==[('ascending',1),('rootbest-first',2)]*2
versions={}
for n in ['preflight-settings-r1.json','pilot-settings-r2.json','later4-settings-r1.json']:
 settings=load(n);versions[n]={pathlib.Path(k).name:v for k,v in settings['sources'].items()if pathlib.Path(k).name in ['protocol.cjs','engine.cjs','arena.cjs']}
fixture=load('clock-fixture-r1.json');fsummary=[{'mode':x['mode'],'adopted':x['adopted'],'status':x['clock']['status'],'elapsed_ms':x['clock']['elapsed_ms'],'cleanup_wait':x['cleanup']['waited']}for x in fixture['results']];assert len(fsummary)==6 and all(x['cleanup_wait']for x in fsummary);assert next(x for x in fsummary if x['mode']=='parse-validation-overshoot')['adopted']is False
stats={}
for e,xs in eng.items():
 es=[x['clock']['elapsed_ms']for x in xs];ps=[x['clock']['response']['search']['stats']['processed']for x in xs];ns=[x['clock']['response']['search']['stats']['NN']for x in xs];stats[e]={'accepted_plies':len(xs),'depth_counts':dict(depths[e]),'stop_counts':dict(stops[e]),'elapsed_ms_min_median_max':[min(es),statistics.median(es),max(es)],'processed_min_median_max':[min(ps),statistics.median(ps),max(ps)],'sum_processed':sum(ps),'sumNN':sum(ns),'inclusive_spans_ms_NOT_EXCLUSIVE':dict(spans[e])}
old=load('pilot-r1-censored-ledger.json');oldhands=sum(1 for _ in (P/'pilot-r1-hands.jsonl').open());
res={'schema':'frame19-native-independent-v1','task':a.task,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PASS':True,'newNN':0,'planned':8,'families':4,'WDL':dict(W),'recorded_main_plies':len(rows),'accepted_plies':len(rows)-len(fault),'faults':fault,'engines':stats,'allattempt':{'knownNN':known,'conservativeNN':charge,'unknown_inflight_upper':charge-known,'guardian_wall_s':wall,'replyNN_accepted_main':nnreply,'replyNN_not_totalphysical':True,'old_censored_hands':oldhands,'old_censor_not_WDL':True},'bench':benchsummary,'protocol_versions':versions,'old_clock_fixture':fsummary,'clock_fixture_current_version_recertified':False,'limits':['shared source receipts; no new forward','four paired opening families, not eight IID','protocol differs preflight/pilot/later; old fixture not new-version recertification','overlapping spans not summed into exclusive cost','no full deep/minimax truth or strength/NI'],'wall_s':time.monotonic()-t}
replayout=pathlib.Path(a.out).with_name('replay-result.json');child=['node','--max-old-space-size=384',str(pathlib.Path(__file__).with_name('replay.cjs')),'--task','frame19-rule-replay-238-v1','--input-manifest',a.input_manifest,'--out',str(replayout)];subprocess.run(child,check=True,capture_output=True,text=True,timeout=35);replay=json.loads(replayout.read_text());assert replay['schema']==res['schema']and replay['task']=='frame19-rule-replay-238-v1'and replay['PASS'];res['rule_replay']=replay;res['wall_s']=time.monotonic()-t
for p,h in manifest['SHA'].items():assert sha(p)==h
pathlib.Path(a.out).write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:res[k]for k in ['PASS','planned','WDL','recorded_main_plies','faults','engines','allattempt','wall_s']}))
