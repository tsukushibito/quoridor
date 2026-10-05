import json,hashlib,pathlib,struct,math,datetime,tarfile
R=pathlib.Path.cwd(); D=R/'research-data/ai-sigma/155-sigma-web-port-games-independent';O=R/'research-data/ai-sigma/151-sigma-web-port';P=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs'
def load(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
r=load(D/'replay-result.json');pre=load(O/'stageB-preregister.json');owner=load(O/'stageB-results.json');science=load(O/'science-runtime-source-stop.json')
assert sha(O/'stageB-results.json')=='dd7ffd8fc10de57031696b8324cf0eaad3f553d7428beed77e3d7e39f3ccbc3e'
assert sha(O/'science-runtime-source-stop.json')=='c86081a4b96cca63934b0e62aa1c82ff86560ca6beeb2fd62635983074ebb304'
refs={};out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'binding':{},'roots':[],'groups':[],'scienceStopSHA':sha(O/'science-runtime-source-stop.json'),'rawResultsSHA':sha(O/'stageB-results.json'),'unknown':['exactAtomicstore','midrunclockdrift','kernelCPU','effectiveCycles','instantRSSpeak','allhost','buildEntireDependencyReadAudit','independentBrowserFetchdigest']}
for p in [O/'stageB-preregister.json',O/'stageB-seed-table.json',O/'stageB-inputs.json',O/'stageB-results.json',O/'science-runtime-source-stop.json']:
 refs[str(p.relative_to(R))]={'SHA256':sha(p),'bytes':p.stat().st_size}
assert pre['input_SHA256']==sha(O/'stageB-inputs.json') and pre['seed_table_SHA256']==sha(O/'stageB-seed-table.json')
seed=load(O/'stageB-seed-table.json')
for s in seed['slots']:
 for a,v in enumerate(s['attempt_seeds']):assert int.from_bytes(hashlib.sha256(f'port151-stageB-v1|master=74021|slot={s["slot"]}|ply={s["layer_ply"]}|attempt={a}'.encode()).digest()[:4],'big')==v
for pair in range(1,9):
 roots=[x for x in r['roots'] if x['pair']==pair];assert len(roots)==2
 nums=[]
 for root in roots:
  n=root['numeric'];v=n['policy_logits']+[n['value']];assert len(v)==137 and len(n['features_bits'])==648
  for x in v:assert math.isfinite(x) and struct.unpack('<f',struct.pack('<f',x))[0]==x
  assert -1<=n['value']<=1
  nums.append([bits(x) for x in v])
 assert nums[0]==nums[1]
 out['roots'].append({'pair':pair,'side':roots[0]['side'],'features648_bit_exact':True,'NN137_numeric_and_bit_exact':True,'legal_order_exact':True,'key':roots[0]['key'],'NN_bits_SHA256':hashlib.sha256(struct.pack('<137I',*nums[0])).hexdigest()})
for g in r['games']:
 x=next(x for x in owner['slots'] if x['id']==g['id']);assert x['winner']==g['winner'] and x['journal_SHA256']==g['journal_sha']
 assert x['normal_terminal'] and x['operational']==[g['score'],g['score']] and x['terminal_quality']==[g['score'],g['score']]
assert owner['fixed_denominator']==16 and owner['pair_denominator']==8
assert r['WDL']==[7,0,9]
out['classification']={'planned':16,'normal_terminal':16,'typedfault':0,'notstarted':0,'infraunknown':0,'operational_identification':[r['mean']]*2,'terminal_quality_identification':[r['mean']]*2,'WDL':r['WDL'],'pairs':r['pairs'],'layers':{str(k):sum(x['Xi'] for x in r['pairs'] if x['layer']==k)/2 for k in [4,5,12,13]},'assumption_only_Hoeffding_eps':math.sqrt(math.log(40)/16),'assumption_only_interval':[max(0,r['mean']-r['eps']),min(1,r['mean']+r['eps'])],'independence_or_coverage_proved':False}
for engine,c in r['counts'].items():
 x=owner['counts'][engine]
 for a,b in [('API','API_started'),('adoptedNN','adopted_NN'),('backup','adopted_backup'),('noNN','last_validated_terminal_noNN'),('returned_discard','API_result_discarded')]:assert c[a]==x[b]
out['counts']=r['counts'];out['startup_separate']=24
allids=set();boot=(R/'/proc/sys/kernel/random/boot_id').read_text().strip()
for group in range(1,5):
 name=f'port151-stageB-group{group}-r1';p=P/name;stop=load(O/(name+'-stop.json'));proc=load(P/(name+'.process.json'));launch=load(P/(name+'.inputs.json'));served=load(p/'actual-served-source.json');binding=load(p/'source-bindings.json');model=load(p/'model-load.json');drop=load(p/'finally-model-drop.json');mon=load(p/'pause-monitor-stop.json');callbacks=load(p/'monitor-callback-stop.json');main=load(p/'main-timers-stop.json');inner=load(p/'outer-controlled-stop.json');workers=load(p/'terminated-worker.json');startup=load(p/'startup.json')
 assert startup['startup_NN']==6 and startup['model_sessions']==2
 assert len(drop['players'])==2 and all(x['handles']==0 and x['activeNN']==0 for x in drop['players'])
 assert main['main_timers']==0 and main['pending_messages']==[]
 assert callbacks=={'timer':False,'busy':False,'waited':True}
 assert mon['state']=='READY' and mon['failure'] is None and mon['pending_children']==[] and mon['all_owned_read_callbacks_waited'] and not mon['active_monitor_timer']
 assert inner['remaining_pids']==0 and inner['forced'] and inner['waited'] and inner['registration_ack']
 assert workers['players']==2 and workers['forced']
 assert stop['outer_ownedwait_returned'] and stop['outer_remaining']==[] and stop['outer_unknown']==[] and proc['kernel_boundary']['sole_explicit_root'] and proc['remaining']==[] and proc['unknown_adopted']==[]
 assert model['threads']==1 and not model['proxy'] and len(model['players'])==2 and all(x['digest']=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d' for x in model['players'])
 for t in proc['tracked']:allids.add((t['pid'],t.get('start_ticks',t.get('starttick'))))
 identities=[]
 for pid,tick in allids:
  try:actual=int(pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
  except FileNotFoundError:continue
  if actual==tick:identities.append({'pid':pid,'starttick':tick})
 assert not identities
 served_current={}
 for route,x in served.items():
  f=pathlib.Path(x['path']);served_current[route]={'saved':x['SHA256'],'current':sha(f) if f.is_file() else None,'is_generated':route in ['/early-page.js','/early-worker.js','/player-base.js','/snapshot-cache.js','/original-worker.js','/puct.wasm']}
 for n in ['game.js','context.js']:
  f=R/'tools/ai-sigma-actual-boundary-repair'/n;assert sha(f)==served['/'+n]['SHA256']
 out['groups'].append({'run':name,'start':proc['start'],'end':proc['end'],'last_game_end_ms':max(x['end_ms'] for x in load(p/'browser-result.json')['games']),'Modeldrop2':drop,'main':main,'callbacks':callbacks,'monitor':{k:mon[k] for k in ['UTC','state','failure','pending_children','all_owned_read_callbacks_waited','active_monitor_timer']},'inner':{k:inner[k] for k in ['remaining_pids','forced','waited','registered','registration_ack']},'outerwait':True,'outer_unknown':proc['unknown_adopted'],'outer_remaining':proc['remaining'],'identity_denominator':len(proc['tracked']),'currentidentity':identities,'boot':proc['kernel_boundary']['boot_id'],'saved_source_commit':launch['git_commit'],'launch_sources':launch['source'],'served':served_current,'source_launch_vs_stop':stop['source_launch_hash']==stop['source_current_hash'],'reader_final_status_file_present':(p/'control-status.json').exists(),'summary':load(p/'summary.json')})
 for n in ['config.json','model-load.json','source-bindings.json','actual-served-source.json','finally-model-drop.json','main-timers-stop.json','monitor-callback-stop.json','pause-monitor-stop.json','outer-controlled-stop.json','terminated-worker.json','startup.json']:
  f=p/n;refs[str(f.relative_to(R))]={'SHA256':sha(f),'bytes':f.stat().st_size}
 for game in r['games']:
  f=p/('completed-game-'+game['id']+'.json')
  if f.exists():refs[str(f.relative_to(R))]={'SHA256':sha(f),'bytes':f.stat().st_size}
out['unique_currentidentity_denominator']=len(allids);out['currentabsence_only']=True
out['clocks']={engine:{'requests':len(v:=[x for x in r['clocks'] if x['engine']==engine]),'public_elapsed_minmax':[min(x['elapsed'] for x in v),max(x['elapsed'] for x in v)],'ACK_minmax':[min(x['ACK_ms'] for x in v),max(x['ACK_ms'] for x in v)],'ownwait_sum':sum(x['own_wait'] for x in v),'other_t0_before_ACK':sum(x['other_t0_before_ACK'] is True for x in v),'publication_end_straddles_cutoff':[x for x in v if x['cutoffMargin']<0<=x['cutoffUpperMargin']],'publication_end_definitely_after_cutoff':[x for x in v if x['cutoffUpperMargin']<0]} for engine in ['candidate','reference']}
manifest=load(O/'archive-manifest.json');restored=[]
for archive in manifest['archives']:
 if 'stageB-group' not in archive['archive']:continue
 f=R/archive['archive'];assert sha(f)==archive['SHA256'];members={m['name']:m for m in archive['members']}
 with tarfile.open(f,'r|gz') as tar:
  for m in tar:
   rel=pathlib.Path('.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT')/m.name
   if str(rel) not in refs:continue
   h=hashlib.sha256();size=0;stream=tar.extractfile(m)
   for b in iter(lambda:stream.read(1024*1024),b''):size+=len(b);h.update(b)
   x=refs[str(rel)];assert size==x['bytes'] and h.hexdigest()==x['SHA256']==members[m.name]['SHA256'];restored.append(str(rel))
out['necessary_archive_stream_restore_count']=len(restored);out['stream_no_full_copy_extract']=True
(D/'input-references.json').write_text(json.dumps(refs,indent=2));(D/'audit-result.json').write_text(json.dumps(out,indent=2));print(json.dumps({'WDL':r['WDL'],'root_pairs_bitexact':len(out['roots']),'groupstop':len(out['groups']),'archive_members':len(restored),'current_absence_identities':len(allids),'clocks':out['clocks']}))
