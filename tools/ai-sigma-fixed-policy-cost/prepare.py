import json,hashlib,pathlib,subprocess,datetime
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/137-fixed-policy-cost';O=R/'.artifacts/ai-sigma/resume-20261002/FIXED-POLICY-COST'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[];refs=[]
for g,r in [(1,'r3'),(2,'r1')]:
 p=R/f'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-QUALITY/runs/quality134-group{g}-{r}/browser-result.json';d=json.loads(p.read_text());game=next(x for x in d['games'] if x['branch']=='A');rid=game['turn_indices'][2];idx=next(i for i,x in enumerate(d['rows']) if x['identity']['request_id']==rid);row=d['rows'][idx];rows.append(row)
 refs.append({'path':str(p),'SHA256':sha(p),'archive_member':str(p).split('LOCAL-MOVE-QUALITY/')[1],'row_index':idx,'request_id':rid,'new_public_index':3,'game_id':game['id']})
a,b=rows
for k in ['legal_prefix','prefix','key','history','model','schema']:assert a['identity'][k]==b['identity'][k],k
na,nb=[r['diagnostic']['numeric'][0] for r in rows];assert na['features_bits']==nb['features_bits'];assert len(na['features_bits'])==648
va=[*na['policy_logits'],na['value']];vb=[*nb['policy_logits'],nb['value']];assert len(va)==137 and all(abs(x-y)<=1e-4+1e-4*abs(y) for x,y in zip(va,vb))
assert a['spec']['physical_side']==b['spec']['physical_side']==1
selected={'identity':a['identity'],'physical_side':1,'totalply':16,'numeric':na,'saved_cp_root_edges':a['diagnostic']['validated_cp']['root_edges'],'source_refs':refs,'sameinput_check':{'identity_fields_exact':True,'features648_exact':True,'NN137_bit_equal':va==vb,'NN137_maxdiff':max(abs(x-y) for x,y in zip(va,vb)),'history_array_record_order_vs_map_semantics':'saved identities canonical sorted; browser replays insertion order then sorted map counts comparison'},'saved_CP_series':[r['diagnostic']['sab_publications'] for r in rows]}
(D/'fixed-input.json').write_text(json.dumps(selected,indent=2)+'\n')
stop=R/'research-data/ai-sigma/135-local-move-independent/runtime-source-stopped-before-report.json';s=json.loads(stop.read_text());ids={}
for x in s['browser_stop']['tracked']:ids[(x['pid'],x['starttick'])]={'pid':x['pid'],'start_ticks':x['starttick']}
for x in s['jobs']:
 for ad in x.get('kernel_adoptions',[]):
  for k in ['observed','launcher_identity','sole_jobroot_identity']:
   i=ad[k];ids[(i['pid'],i['start_ticks'])]={'pid':i['pid'],'start_ticks':i['start_ticks']}
# Add recorded owner/child identities from original managed records, via readonly archive extraction if needed.
prefs=[]
for p in (R/'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-INDEPENDENT').glob('**/*.process.json'):
 d=json.loads(p.read_text());prefs.append({'path':str(p),'SHA256':sha(p)})
 for i in d.get('tracked',[]):ids[(i['pid'],i['start_ticks'])]={'pid':i['pid'],'start_ticks':i['start_ticks']}
 for pre in ['runner','child']:
  if d.get(pre+'_pid') and d.get(pre+'_starttick'):ids[(d[pre+'_pid'],d[pre+'_starttick'])]={'pid':d[pre+'_pid'],'start_ticks':d[pre+'_starttick']}
(O/'dependency135-identities.json').write_text(json.dumps({'identities':list(ids.values()),'process_refs':prefs},indent=2)+'\n')
pr={'issue':'quoridor-4lc.137','input_file':str(D/'fixed-input.json'),'input_SHA256':sha(D/'fixed-input.json'),'physical_side':1,'engine':'candidate','actual_policy_both_slots':'fixedSigma C1/FPU.2/first/temp0/originalorder','requests':[{'id':'warm','warm':True},{'id':'sample1','warm':False},{'id':'sample2','warm':False},{'id':'sample3','warm':False}],'startup_NN':6,'session_count':2,'seed':1979,'T_ms':500,'cutoff_ms':402,'adopt_ms':411,'sample_interval_ms':5,'SAB_bounded_samples':2,'numeric_tolerance':{'abs':1e-4,'rtol':1e-4},'CPU_TID_observation_interval_ms':100,'root_CP_capture':'after original SAB publication, readonly copy; overhead not calibrated','root_count':'root initialization outside loop; completed_backup=root_visits=1+loop simulations, edge visits sum=loop simulations; terminal backup noNN separate','previous_Git_refs':{'134_source':'6b79eca','134_data':'7af1635','134_handoff':'bd339e2','136_data':'d13bd5b5','136_handoff':'05d20e4','contract':'1c94c2036f8242c54cc36a597957a74d4fc0edaa'},'no_successful_retry':True,'fixed_before_new_NN':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(D/'preregister.json').write_text(json.dumps(pr,indent=2)+'\n')
intake=json.loads((D/'intake.json').read_text());print(intake)
c={'issue':'quoridor-4lc.137','frame':9,'run_id':'cost137-r1','kind':'cost','seed':1979,'adopt_ms':411,'sample_interval_ms':5,'preregister':str(D/'preregister.json'),'preregister_SHA256':sha(D/'preregister.json'),'dependency_stop':str(stop),'dependency_stop_SHA256':sha(stop),'dependency_identities':str(O/'dependency135-identities.json'),'forecast_bytes':16*1024*1024,'minimum_remaining_heavy_seconds':30,'pin_owned_TIDs':True,'processing_deadline':'2026-10-02T18:15:29.388935+00:00','newjob_deadline':'2026-10-02T18:10:29.388935+00:00','submission_deadline':'2026-10-02T18:25:29.388935+00:00'}
(D/'config.json').write_text(json.dumps(c,indent=2)+'\n')
print(json.dumps({'same_input':selected['sameinput_check'],'input_SHA':pr['input_SHA256'],'dependency_SHA':sha(stop),'identities':len(ids)}))
