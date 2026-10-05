"""Saved rows only: no model, RuleA, forward or new game."""
from pathlib import Path
import json,hashlib,datetime,collections,statistics
R=Path.cwd();D=R/'research-data/ai-sigma/frame20-distance-arena';manifest=json.loads((D/'openings8-v1.json').read_text());slots={str(s['slot']):dict(s) for s in manifest['slots']};hands=[];jobs=[]
for run in ['family0-r1','family1-r1']:
 p=D/(run+'-result.json')
 if p.exists():
  x=json.loads(p.read_text());assert x['task']=='frame20-distance-arena-249-v1'and x['schema']=='distance-arena-v1'
  for s in x['ledger']:
   if s['slot']in x['attempted_slots']:slots[str(s['slot'])]=s
  jobs.append(x)
 p=D/(run+'-hands.jsonl')
 if p.exists():hands.extend(json.loads(line)for line in p.read_text().splitlines())
cohorts={};matches=[];index=collections.defaultdict(dict)
for h in hands:
 c=h['clock'];response=c.get('response')or{};search=response.get('search')or{};stats=search.get('stats',{});key=h['distance_mode']+'/'+h['engine'];co=cohorts.setdefault(key,dict(hands=0,adopted=0,unknown=0,depths=collections.Counter(),processed=0,NN=0,D_evals=0,terminal=0,D_nonterminal_saturated=0,nodecap_hits=0,late_valid=0,partialdiscard=0,slack=[],raw_min=[],raw_max=[]));co['hands']+=1
 valid=c['status']=='RECEIVED'and response.get('validation',{}).get('valid')is True
 if valid:
  assert c['elapsed_ms']<=100 and response['generation']==h['generation']and response['id']==h['id']and response['key']==h['before_key']and response['history']==h['before_history']
  assert response['distance_mode']==h['distance_mode']and search['distance_mode']==h['distance_mode'];co['adopted']+=1;co['depths'][search['completed_depth']]+=1;co['slack'].append(100-c['elapsed_ms'])
 else:co['unknown']+=1
 if c['elapsed_ms']>100 and response.get('validation',{}).get('valid'):co['late_valid']+=1
 for k in ['processed','NN','D_evals','terminal','D_nonterminal_saturated']:co[k]+=stats.get(k,0)
 co['nodecap_hits']+=int(search.get('typed_stop')=='NODE_CAP');co['partialdiscard']+=int(search.get('partial_depth_discarded')is not None)
 for k in ['min','max']:
  if stats.get('D_raw_'+k)is not None:co['raw_'+k].append(stats['D_raw_'+k])
 slot=slots[str(h['slot'])];hist=json.loads(h['before_history']);signature=json.dumps([slot['family'],slot['NNUE_side'],h['engine'],hist],sort_keys=True,separators=(',',':'));index[signature][h['distance_mode']]=h
for sig,pair in index.items():
 if set(pair)!=set(['clip','tanh']):continue
 a,b=pair['clip'],pair['tanh'];ra=(a['clock'].get('response')or{}).get('search',{});rb=(b['clock'].get('response')or{}).get('search',{});common=[]
 for x in ra.get('depths',[]):
  if x['status']!='COMPLETED':continue
  y=next((y for y in rb.get('depths',[])if y['status']=='COMPLETED'and y['completed_depth']==x['completed_depth']),None)
  if y:common.append(dict(depth=x['completed_depth'],clip_value=x['value'],tanh_value=y['value'],value_delta=y['value']-x['value'],clip_Action=x['Action'],tanh_Action=y['Action'],Action_changed=x['Action']!=y['Action']))
 matches.append(dict(engine=a['engine'],slot_clip=a['slot'],slot_tanh=b['slot'],ply=a['ply'],input_history_SHA=hashlib.sha256(a['before_history'].encode()).hexdigest(),exact_prefix_equal=a['before_prefix']==b['before_prefix'],clip_depth=ra.get('completed_depth'),tanh_depth=rb.get('completed_depth'),clip_Action=ra.get('Action'),tanh_Action=rb.get('Action'),common=common,equal_argmax='NOT_RECORDED',all_exact_children='NOT_RECORDED'))
for co in cohorts.values():
 co['minimum_slack_ms']=min(co.pop('slack'),default=None);co['D_raw_min']=min(co.pop('raw_min'),default=None);co['D_raw_max']=max(co.pop('raw_max'),default=None);co['D_pretransform_absu_ge1_fraction']=co['D_nonterminal_saturated']/co['D_evals']if co['D_evals']else None;co['counter_endpoint_claim']=False
WDL={}
for mode in ['clip','tanh']:
 chosen=[s for s in slots.values()if s['distance_mode']==mode];WDL[mode]={k:sum(s.get('result_NNUE')==k for s in chosen)for k in ['W','D','L']};WDL[mode].update({k:sum(s['status']==k for s in chosen)for k in ['TERMINAL','UNKNOWN','NOT_STARTED']});WDL[mode]['planned']=len(chosen)
receipts=[json.loads(p.read_text())for p in(D/'guardians').glob('*/process.json')];background=[json.loads(p.read_text())for p in D.glob('background-*/result.json')]
out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':'frame20-distance-arena-249-v1','schema':'distance-arena-v1','planned':8,'slots':list(slots.values()),'WDL_NNUE':WDL,'hands':len(hands),'cohorts':cohorts,'matched_inputs':len(matches),'matched':matches,'science_samples_known':sum(x['samples_actual']or 0 for x in receipts),'science_samples_charge':sum(x['samples_charge']for x in receipts),'science_guardianwall_s':sum(x['wall_s']for x in receipts),'job_init_ready_ms':[x['init_to_ready_ms']for x in jobs],'job_controllerwall_ms':[x['wholewall_ms']for x in jobs],'science_process':receipts,'background':background,'limits':['tanh changes all nonterminal u and CPU cost,not saturation-only','aggregate different reachable states not fixedwork','same2prefix diagnostic not independent8opening','WDL relative; both keep same NNUE and search,not NI/higheststrength','commondepth no all-exact argmax guarantee']}
(D/'aggregate-v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['WDL_NNUE','hands','matched_inputs','science_samples_known','science_samples_charge','science_guardianwall_s']}))
