import pathlib,json,subprocess,tarfile,io,hashlib,datetime,statistics,math,sys
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA-INDEPENDENT';B='research-data/ai-sigma/103-cooperative-arena/';args=sys.argv[1:] or ['initial-pair-r1=9dd49a00c77133a199401fd84efdac6c60abcba7','asym-pair-r1=137b6bddd86eddfab4e61bebafb44988383f582b'];outputs=[];nodes=[];ledger=[]
def compact(x):return json.dumps(x,separators=(',',':'),ensure_ascii=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def stats(v):return {'n':len(v),'median':statistics.median(v),'max':max(v)} if v else {'n':0}
for arg in args:
 run,git=arg.split('=');manifest=json.loads(subprocess.check_output(['git','show',git+':'+B+run+'.archive-manifest.json']));ab=subprocess.check_output(['git','show',git+':'+B+run+'.tar.gz']);assert sha(ab)==manifest['archive_sha256'];t=tarfile.open(fileobj=io.BytesIO(ab),mode='r:gz');matched={}
 def get(name):
  b=t.extractfile(name).read();assert sha(b)==manifest['restored_hashes'][name],name;matched[name]={'SHA':sha(b),'bytes':len(b)};return b
 def read(name):return json.loads(get(run+'/'+name))
 def lines(name):return [json.loads(l) for l in get(run+'/'+name).splitlines() if l]
 cfg=read('config.json');summary=read('summary.json');starts=lines('game-start.jsonl');moves=lines('moves.jsonl');pub=lines('public.jsonl');turns=lines('turns.jsonl');backend='real-'+run+'-session1/';priv=read(backend+'private-after-public.json');by={v['identity']['request_id']:v for v in pub};assert len(by)==len(pub)==len(turns)==len(moves)
 assert cfg['seed']==1979 and cfg['clock']=={'T':500,'reserve':89,'commit':9,'cutoff':402,'seal':411} and cfg['tail_condition']=='cooperative';assert cfg['NNthreads']==1 and cfg['affinity']==[2];assert cfg['candidate_color_order']==[1,2];assert [v['candidateColor'] for v in starts]==[1,2];assert len(starts)==2;assert [v['game'] for v in starts]==[cfg['games_before']+1,cfg['games_before']+2]
 for e in starts:assert e['prefix_sha256']==cfg['prefix_sha256'] and e['seed']==1979
 small=[];samples={};seen_sample_keys=set();marker=[];late=[];NN=0;apiDef=apiPossible=afterPubD=afterPubP=wrapperAfter=0;classCounts={};ACKlate=[];ownedStopSamples=[];clockProof={}
 for row,move in zip(turns,moves):
  p=by[row['request_id']];id=p['identity'];resp=p['response'];assert move['response']==resp;assert move['engine']==id['engine']==row['engine'];assert id['legal_prefix']==move['prefix'];assert resp['echo']==id;assert id['generation']==id['epoch'];assert id['limits']['seed']==1979;assert id['model']==cfg['model_sha256'];assert id['request_token']==id['request_id'];assert resp['stamp_ms']==row['public_stamp_ms'];assert resp['referee_verified'] is True and isinstance(resp['accepted'],bool) and isinstance(resp['checkpoint'],bool);assert (resp['stamp_ms']>=id['deadline_ms'])==resp['late'];assert len(resp['public_json'].encode())==resp['public_bytes'];body=json.loads(resp['public_json']);assert body['action']==resp['action'] and body['accepted']==resp['accepted'] and body['referee_action']==resp['referee_action'] and body['error']==resp['error'];assert body['checkpoint']==resp['checkpoint'];assert id['deadline_ms']-id['t0_ms']==500 and id['commit_cutoff_ms']-id['t0_ms']==402
  a=row['owned_zero'];assert a['handles']==a['activeNN']==a['live_searches']==0 and a['active'] is False and not a['ownership_error'];assert abs((resp['stamp_ms']-id['t0_ms'])-row['public_elapsed_ms'])<1e-6
  if small:assert id['t0_ms']>=small[-1]['ACKstamp']
  # Each finish saved the same final body: no post-finish Action reselection.
  fin=read(backend+'public-'+id['request_id']+'.json');assert fin['response']==resp
  cp=row['root_cp'];
  if resp['accepted']:assert cp and cp['action']==resp['action'] and resp['checkpoint'] and resp['error'] is None and resp['fallback']==0 and math.isfinite(resp['value']) and abs(resp['value'])<=1
  else:assert resp['action'] is None and resp['checkpoint'] is False and resp['value'] is None;late.append({'request_id':id['request_id'],'game':move['game'],'engine':row['engine'],'ply':move['ply'],'public_elapsed':resp['stamp_ms']-id['t0_ms'],'cause':row['stop_ACK_ms']-id['t0_ms'],'error':resp['error'],'encoded_body_error':body['error'],'cache_raw_stamp_elapsed':row['cache_caller_stamp_ms']-id['t0_ms'],'final_Judge_UTF8_ms':row['shared_final_Judge_clone_UTF8_ms'],'snapshot_cp_present':cp is not None})
  c=row['worker_clock'];stop=read(backend+'stopACK-'+id['request_id']+'.json');S=stop['stop']['at_ms'];lo=S-c['hi_ms'];hi=S-c['lo_ms'];assert abs(lo-row['Worker_stop_interval']['early_ms'])<1e-6 and abs(hi-row['Worker_stop_interval']['late_ms'])<1e-6;classify='upper_le_D' if hi<=id['deadline_ms'] else 'lower_gt_D' if lo>id['deadline_ms'] else 'straddles_D';assert classify==row['Worker_stop_class'];classCounts[classify]=classCounts.get(classify,0)+1
  receive=stop['node_received_ms'];assert abs(receive-row['stop_node_received_ms'])<1e-6;assert abs(receive-hi-row['stop_to_Node_interval']['lo_ms'])<1e-6;assert abs(receive-lo-row['stop_to_Node_interval']['hi_ms'])<1e-6;assert abs(row['stop_ACK_ms']-receive-row['Node_received_to_confirm_ms'])<1e-6
  n=priv[id['request_id']]['NN'];assert len(n)==row['NN_completed']==len(row['API_spans']);NN+=len(n);after=0;APIcross=[]
  for call,span in zip(n,row['API_spans']):
   early=call['session_run_start_ms']-c['hi_ms'];last=call['session_run_start_ms']-c['lo_ms'];assert abs(early-span['start_early_ms'])<1e-6 and abs(last-span['start_late_ms'])<1e-6;assert abs(call['session_run_end_ms']-call['session_run_start_ms']-span['api_await_ms'])<1e-6
   if call['awaiter_start_ms']>=id['commit_cutoff_ms']+c['lo_ms']:after+=1
   if early>id['commit_cutoff_ms']:apiDef+=1
   if last>id['commit_cutoff_ms']:apiPossible+=1;APIcross.append({'early_elapsed':early-id['t0_ms'],'late_elapsed':last-id['t0_ms'],'awaiter_elapsed_early':call['awaiter_start_ms']-c['hi_ms']-id['t0_ms'],'awaiter_elapsed_late':call['awaiter_start_ms']-c['lo_ms']-id['t0_ms'],'internal_start_minus_wrapper_start':call['session_run_start_ms']-call['awaiter_start_ms']})
   afterPubD+=early>resp['stamp_ms'];afterPubP+=last>resp['stamp_ms']
  assert after==row['NN_start_after_cutoff_worker'];wrapperAfter+=after
  # Complete cache assignment is timed by SnapshotCache's last_gate, not caller's later marker.
  for b in row['bindings']:
   if b['accepted'] and b['kind']=='snapshot':
    gate=b['last_gate'];assert gate['validated_cache_ms']<id['commit_cutoff_ms'];assert gate['validation_finished_ms']==gate['validated_cache_ms'];assert gate['accepted'] is True
    if b['node_validation_finished_ms']>=id['commit_cutoff_ms']:marker.append({'request_id':id['request_id'],'engine':id['engine'],'cutoff':id['commit_cutoff_ms'],'producer_times':b['raw_source_times'],'Node_received':b['node_received_ms'],'validation_finished':gate['validation_finished_ms'],'cache_commit_marker':gate['validated_cache_ms'],'caller_marker':b['node_validation_finished_ms'],'caller_after_cutoff':b['node_validation_finished_ms']-id['commit_cutoff_ms'],'committed_before_cutoff':id['commit_cutoff_ms']-gate['validated_cache_ms'],'sequence':b['sequence']})
  cpu=row['cpu'];assert cpu['identity_public']['valid_observed_monotonic'] and cpu['identity_residual']['valid_observed_monotonic'];assert cpu['identity_public']['observed_delta_ticks']==cpu['browser_public_ticks'];assert cpu['identity_residual']['observed_delta_ticks']==cpu['browser_residual_ticks']
  q={'id':id['request_id'],'engine':id['engine'],'game':move['game'],'ply':move['ply'],'t0':id['t0_ms'],'publicstamp':resp['stamp_ms'],'publicelapsed':resp['stamp_ms']-id['t0_ms'],'ACKstamp':row['stop_ACK_ms'],'ACKwall':row['stop_ACK_ms']-id['t0_ms'],'WorkerstopLower':lo-id['t0_ms'],'WorkerstopUpper':hi-id['t0_ms'],'stop_delivery_interval':[receive-hi,receive-lo],'Node_receive_to_ACKconfirm':row['stop_ACK_ms']-receive,'NN':len(n),'wrapperAfterCutoff':after,'internalAPICrossCutoff':APIcross,'public_before_D':resp['accepted'],'action':resp['action'],'error':resp['error'],'CPU_public_observed_ticks':cpu['browser_public_ticks'],'CPU_residual_observed_ticks':cpu['browser_residual_ticks'],'shared_public_log_ms':row['shared_public_log_ms'],'shared_inspection_ms':row['shared_diagnostic_inspection_ms']};small.append(q)
  if q['ACKwall']>500:ACKlate.append(q)
  # Each engine/color, initial fixed-golden roots, and both rejected outputs.
  key=(id['engine'],len(id['legal_prefix'])%2)
  if key not in seen_sample_keys or not resp['accepted'] or len(id['legal_prefix'])==len(moves[0]['prefix']):
   seen_sample_keys.add(key);samples[str(id['request_id'])]={'identity':id,'numeric':row['root_numeric'],'cp':row['root_cp'],'response_value':resp['value'],'accepted':resp['accepted'],'error':resp['error']}
 for phase in ['start','end']:
  cs=read(backend+'browser/clock-'+phase+'.json');clockProof[phase]={}
  for channel in ['page','worker']:
   c=cs[channel];assert len(c['samples'])==12;lo=max(v['remote']-v['end']-.1 for v in c['samples']);hi=min(v['remote']-v['start']+.1 for v in c['samples']);assert abs(lo-c['lo_ms'])<1e-6 and abs(hi-c['hi_ms'])<1e-6;assert lo<=hi;clockProof[phase][channel]=[lo,hi]
 for k in ['page','worker']:assert max(clockProof['start'][k][0],clockProof['end'][k][0])<=min(clockProof['start'][k][1],clockProof['end'][k][1])
 drop=read(backend+'model-drop.json');controlled=read(backend+'controlled-stop.json');mon=read('pause-monitor-stop.json');assert drop['handles']==drop['activeNN']==0;assert controlled['controlledPID0'] and controlled['cleanup']['remaining_pids']==0 and controlled['cleanup']['waited'];assert not mon['pending_children'] and mon['all_owned_read_callbacks_waited'];assert not mon['active_monitor_timer']
 assert NN==summary['NN_hand'];assert summary['startup']['root_NN']==6
 # Smaller replay input contains one starting prefix/game, then only proposed actions.
 gameInput=[]
 for s in starts:
  mm=[v for v in moves if v['game']==s['game']];store=next(g['result'] for g in summary['games'] if g['game']==s['game']);entries=[]
  for m in mm:
   resp=m['response'];id=by[resp['request_id']]['identity'];assert m['prefix']==id['legal_prefix'];entries.append({'ply':m['ply'],'engine':m['engine'],'color':m['color'],'proposed':resp['referee_action'],'action':resp['action'],'accepted':resp['accepted'],'error':resp['error'],'late':resp['late'],'id':resp['request_id'],'generation':resp['generation'],'t0':id['t0_ms'],'stamp':resp['stamp_ms'],'D':id['deadline_ms'],'prefix_sha':resp['prefix_sha256'],'history_sha':resp['history_sha256'],'key':resp['position_key'],'encoded':json.loads(resp['public_json'])['accepted']})
  gameInput.append({'game':s['game'],'candidateColor':s['candidateColor'],'initial':mm[0]['prefix'],'entries':entries,'storedResult':store})
 out={'run':run,'dataGit':git,'runtimeGit':cfg['git'],'public':len(pub),'accepted':sum(v['response']['accepted'] for v in pub),'late':sum(v['response']['late'] for v in pub),'handNN':NN,'startupNN':6,'wrapperStartsAfterEarlyCutoff':wrapperAfter,'internalAPIdefinitelyAfter402':apiDef,'internalAPIpossiblyAfter402':apiPossible,'internalAPIdefinitelyAfterPublic':afterPubD,'internalAPIpossiblyAfterPublic':afterPubP,'Workerstop':classCounts,'ACKwallOver500':len(ACKlate),'late_details':late,'marker_after_commit_before':marker,'clockProof':clockProof,'config':cfg,'owned_cleanup':{'Modeldrop':drop,'controlled_forced':controlled['forced'],'controlledPID0':controlled['controlledPID0'],'controlled_tracked':controlled['cleanup']['tracked'],'outer_saved_proof_not_yet_final':True,'monitor':{k:mon[k] for k in ['state','failure','pending_children','all_owned_read_callbacks_waited','active_monitor_timer']}},'summary_owner_WDL_not_used_as_independent_result':{k:summary[k] for k in ['W','D','L']},'raw_member_hashes':matched,'perturn':small}
 outputs.append(out);nodes.append({'run':run,'runtimeGit':cfg['git'],'config':cfg,'games':gameInput,'samples':list(samples.values())});ledger.append({'git':git,'archive':run+'.tar.gz','archiveSHA':manifest['archive_sha256'],'manifest_SHA_semantic_compact_not_original_bytes':sha(compact(manifest).encode()),'matched_members':len(matched)})
(O/'independent-clock-arithmetic-final.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':outputs,'archiveBindings':ledger,'API_await_not_kernel_time':True},indent=2)+'\n');(O/'replay-numeric-input-final.json').write_text(json.dumps(nodes,separators=(',',':'))+'\n')
for r in outputs:print(json.dumps({k:r[k] for k in ['run','public','accepted','late','handNN','wrapperStartsAfterEarlyCutoff','internalAPIdefinitelyAfter402','internalAPIpossiblyAfter402','Workerstop','ACKwallOver500','late_details','marker_after_commit_before']}))
