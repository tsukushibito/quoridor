"""246 single dedicated NN0 saved arithmetic; no models or old data checkers."""
import argparse,collections,hashlib,json,math,pathlib,subprocess,time,os
ap=argparse.ArgumentParser();ap.add_argument('--task',required=True);ap.add_argument('--input-manifest',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();assert a.task=='frame20-paired-independent-246-v1'
P=pathlib.Path('research-data/ai-sigma/frame19-paired-leaf-arena');D=pathlib.Path(a.out).parent;T=pathlib.Path('tools/ai-sigma-frame20-paired-independent');sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();inp=json.loads(pathlib.Path(a.input_manifest).read_text())
for p,h in inp['SHA'].items():assert sha(p)==h,p
read=lambda n:json.loads((P/n).read_text());m=read('openings8-v1.json');ledger=read('all8-final-ledger.json')['ledger'];assert len(ledger)==8 and sorted(g['slot']for g in ledger)==list(range(1,9));planned={s['slot']:s for s in m['slots']};wd={False:collections.Counter(),True:collections.Counter()};rows=[];slots=[]
for g in ledger:
 s=planned[g['slot']];assert all(g[k]==s[k]for k in ['opening','family','leaf_package','NNUE_side','D_side']);assert g['status']=='TERMINAL';o=next(o for o in m['openings']if o['id']==s['opening']);assert g['prefix'][:o['opening_ply']]==o['prefix'];wd[g['leaf_package']][g['result_NNUE']]+=1;slots.append({k:g[k]for k in ['slot','opening','family','leaf_package','NNUE_side','hands','winner','result_NNUE']})
assert all(wd[v]=={'W':2,'L':2}for v in wd)
for name in ['family0-r1-hands.jsonl','family1-r1-hands.jsonl']:
 lastgen=0
 for line in (P/name).open():
  h=json.loads(line);c=h['clock'];r=c['response'];q=r['search'];g=next(x for x in ledger if x['slot']==h['slot']);assert c['status']=='RECEIVED'and 0<=c['elapsed_ms']<=100 and abs(c['received_ms']-c['t0_ms']-c['elapsed_ms'])<1e-6;assert r['id']==h['id']and r['generation']==h['generation']and h['generation']>lastgen;lastgen=h['generation'];assert r['leaf_package']==q['leaf_package']==g['leaf_package'];assert r['validation']['valid']and r['validation']['legal']and r['validation']['value_finite'];assert q['status']=='COMPLETED_ACTION'and q['completed_depth']>=1 and q['last_completed_only']and q['parent_copy_key_history_restored'];assert math.isfinite(q['value']);assert q['node_cap']==32768 and q['stats']['processed']<=32768;assert h['engine']==('NNUE'if h['side']==g['NNUE_side']else'distance');assert r['key']==q['root_key']and r['history']==q['root_history'];ds=[d for d in q['depths']if d['status']=='COMPLETED'];assert ds[-1]['completed_depth']==q['completed_depth']and ds[-1]['Action']==q['Action']and ds[-1]['value']==q['value'];assert all(d.get('adopted')is False for d in q['depths']if d['status']=='INCOMPLETE');rows.append({**h,'variant':g['leaf_package']})
assert len(rows)==sum(g['hands']for g in ledger)==338
metrics=[]
for v in [False,True]:
 for e in ['NNUE','distance']:
  hs=[h for h in rows if h['variant']==v and h['engine']==e];qs=[h['clock']['response']['search']for h in hs];clock=[h['clock']['elapsed_ms']for h in hs];metrics.append({'variant':'candidate'if v else'baseline','engine':e,'hands':len(hs),'completeddepth_counts':dict(collections.Counter(q['completed_depth']for q in qs)),'depth_mean':sum(q['completed_depth']for q in qs)/len(qs),'processed':sum(q['stats']['processed']for q in qs),'NN':sum(q['stats']['NN']for q in qs),'cap_reached':sum(q['stats']['processed']==32768 for q in qs),'clock_mean_ms':sum(clock)/len(clock),'clock_max_ms':max(clock),'slack_min_ms':100-max(clock),'searchwhole_sum_ms':sum(q['wholewall_ms']for q in qs),'partial_discarded':sum(q['partial_depth_discarded']is not None for q in qs)})
paired=[];common=[]
for opening in m['openings']:
 for side in [1,2]:
  gs=[g for g in ledger if g['opening']==opening['id']and g['NNUE_side']==side];assert len(gs)==2
  base=next(g for g in gs if not g['leaf_package']);cand=next(g for g in gs if g['leaf_package']);index=collections.defaultdict(list)
  key=lambda h:(h['engine'],h['side'],h['clock']['response']['key'],h['clock']['response']['history'])
  for h in rows:
   if h['slot']==cand['slot']:index[key(h)].append(h)
  for b in [h for h in rows if h['slot']==base['slot']]:
   if not index[key(b)]:continue
   c=index[key(b)].pop(0);qb=b['clock']['response']['search'];qc=c['clock']['response']['search'];db={d['completed_depth']:d for d in qb['depths']if d['status']=='COMPLETED'};dc={d['completed_depth']:d for d in qc['depths']if d['status']=='COMPLETED'};cmp=[]
   for depth in sorted(db.keys()&dc.keys()):
    x,y=db[depth],dc[depth];gap=abs(x['value']-y['value']);cmp.append({'depth':depth,'value_maxabs':gap,'Action_equal':x['Action']==y['Action']});common.append(cmp[-1])
   paired.append({'baseline_slot':base['slot'],'candidate_slot':cand['slot'],'engine':b['engine'],'input_SHA':hashlib.sha256(repr(key(b)).encode()).hexdigest(),'baseline_depth':qb['completed_depth'],'candidate_depth':qc['completed_depth'],'processed_delta':qc['stats']['processed']-qb['stats']['processed'],'NN_delta':qc['stats']['NN']-qb['stats']['NN'],'elapsed_delta_ms':c['clock']['elapsed_ms']-b['clock']['elapsed_ms'],'common':cmp})
profiles=[]
for e in ['NNUE','distance']:
 ps=[p for p in paired if p['engine']==e];profiles.append({'engine':e,'sameinput_pairs':len(ps),'deeper':sum(p['candidate_depth']>p['baseline_depth']for p in ps),'equaldepth':sum(p['candidate_depth']==p['baseline_depth']for p in ps),'shallower':sum(p['candidate_depth']<p['baseline_depth']for p in ps),'processed_delta_sum':sum(p['processed_delta']for p in ps),'NN_delta_sum':sum(p['NN_delta']for p in ps),'elapsed_delta_mean_ms':sum(p['elapsed_delta_ms']for p in ps)/len(ps)})
processes=[json.loads(p.read_text())for p in sorted((P/'guardians').glob('*/process.json'))];assert len(processes)==3;known=sum(p['samples_actual']for p in processes);wall=sum(p['wall_s']for p in processes);assert known==258903 and abs(wall-31.73198343697004)<1e-8;assert sum(x['NN']for x in metrics)==known-5500
childcmd=['node','--max-old-space-size=384',str(T/'replay-paired.cjs'),'--task','frame20-paired-replay-246-v1','--out',str(D/'replay.json')];p=subprocess.Popen(childcmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);stat=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split();tick=stat[19];stdout,stderr=p.communicate(timeout=35);assert p.returncode==0,stderr.decode();assert not pathlib.Path('/proc',str(p.pid)).exists();replay=json.loads((D/'replay.json').read_text());assert replay['PASS']and replay['adopted']==338;childrec={'argv':childcmd,'PID':p.pid,'tick':tick,'exit':0,'wait':True,'current_exact_absent':True}
for p,h in inp['SHA'].items():assert sha(p)==h,'changed '+p
result={'task':a.task,'schema':'paired-independent-v1','PASS':True,'newNN':0,'planned8':8,'terminal8':8,'UNKNOWN':0,'NOT_STARTED':0,'pervariantWDL':{'baseline':dict(wd[False]),'candidate':dict(wd[True])},'slots':slots,'adopted338':len(rows),'metrics':metrics,'sameinput':profiles,'commondepth_columns':len(common),'common_value_maxabs':max(x['value_maxabs']for x in common),'common_Action_differences':sum(not x['Action_equal']for x in common),'pairs':paired,'knownNN':known,'guardian_wall_s':wall,'sharedRuleA':replay,'child':childrec,'all_exact_argmax':'NOT_RECORDED','management_save_unknown':'UNKNOWN; overlapping background elapsed not added','limits':['2 openings/families color swaps; small fixed order','package applied to both engines; no absolute strength effect identified','aggregate differing states not matchedwork','sharedRuleA and owner saved search numerical receipts; no forward/deep truth','old241 fixedwork speed and samewall WDL different questions','oldtest173 unread; old229 final NOT_RUN unchanged']}
pathlib.Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['pairs','sharedRuleA','slots']}))
