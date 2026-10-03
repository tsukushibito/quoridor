import pathlib,json,gzip,hashlib,struct,math,time,datetime,resource,os,collections,traceback,statistics,gc
os.sched_setaffinity(0,{0});D=pathlib.Path('research-data/ai-sigma/191-manygame-independent');A=pathlib.Path('research-data/ai-sigma/187-manygame-generation');B=pathlib.Path('.artifacts/ai-sigma/resume-20261003/MANYGAME-GENERATION');start=time.monotonic();result={'issue':'quoridor-4lc.191','NN_executed':0,'first_difference':None};snap={}
def load(p):
 b=p.read_bytes();snap[str(p)]={'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return json.loads(b)
def require(v,msg):
 if not v:raise AssertionError(msg)
def f32(b):return struct.unpack('<f',struct.pack('<I',b))[0]
def enc(x):return json.dumps(x,separators=(',',':'))
try:
 openings=load(A/'openings.json');specs={s['game_id']:s for s in openings['games']};ranked=sorted(specs.values(),key=lambda s:s['split_hash']);require(len(specs)==24,'24 inputs');require(all(s['split_hash']==hashlib.sha256(('NATIVE187_SPLIT_V1|'+s['family']).encode()).hexdigest()and s['split']==('validation'if s in ranked[:4]else'train')for s in specs.values()),'preregister split')
 outputs=[];quality_status=collections.Counter();totalrows=0;baseline={};modes=['CPUJS','RustCPU','GPU3','GPU12','GPU24']
 for mode in modes:
  run='native187-'+mode.lower()+'-r1';path=B/run;rows=[json.loads(l)for l in gzip.open(A/(mode+'-teacher-rows.jsonl.gz'),'rt')if l.strip()];games=load(A/(mode+'-all-status.json'));G={g['game_id']:g for g in games};owner=load(A/(mode+'-summary.json'));proc=load(path/'process.json');rawresult=load(path/'result.json');require(len(games)==len(G)==24 and set(G)==set(specs),'24 slots '+mode);require(not proc['remaining'],'owned remaining '+mode);require(rawresult['planned_games']==24,'raw plan '+mode)
  seen=set();groups=[collections.defaultdict(list)for _ in range(4)];directions=[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)];flip=[1,0,2,3,6,7,4,5];p2jump=p2wall=0;counts=collections.Counter();NN=terminal=discard=0
  for r in rows:
   rid=r['row_id'];require(rid not in seen,rid+' duplicate');seen.add(rid);g=G[r['game_id']];s=specs[r['game_id']];require(r['family']==g['family']==s['family']and r['lineage']==s['family']+'|'+mode,rid+' lineage');split=s['split'];require(r['split']==split==s['split'],rid+' split');require(r['family'].startswith('native187-'),rid+' holdout domain')
   require(r['rootN']==64 and r['edgeSum']==63,rid+' K');require(r['NN_completed']+r['terminal_noNN']==64 and r['NN_discarded']==0,rid+' NN');NN+=r['NN_completed'];terminal+=r['terminal_noNN'];require(r['legal_mask136']==[int(k in set(k for a,k in r['mapping136']))for k in range(136)],rid+' legal mask')
   require(len(r['visits136'])==len(r['pi136'])==136 and sum(r['visits136'])==63,rid+' visits');require(all(isinstance(v,int)and v>=0 for v in r['visits136']),rid+' noninteger visits');require(len(r['mapping136'])==len(r['legal_order209'])and [a for a,k in r['mapping136']]==r['legal_order209'],rid+' order');require(len(set(a for a,k in r['mapping136']))==len(r['mapping136'])and len(set(k for a,k in r['mapping136']))==len(r['mapping136']),rid+' mask injectivity')
   parts=r['state_key'].split('|');pawn=list(map(int,parts[r['side']-1].split(',')));opp=list(map(int,parts[2-r['side']].split(',')));legal=set()
   for a,k in r['mapping136']:
    if a>=81:
     v=a>=145;offset=145 if v else 81;x=(a-offset)%8;y=(a-offset)//8;expect=8+(64 if v else 0)+8*(7-y if r['side']==2 else y)+x;p2wall+=int(r['side']==2)
    else:
     dest=[a%9,a//9];dx=dest[0]-pawn[0];dy=dest[1]-pawn[1]
     if abs(dx)==2 or abs(dy)==2:dx//=2;dy//=2;p2jump+=int(r['side']==2)
     require((dx,dy)in directions,rid+' destination');k0=directions.index((dx,dy));expect=flip[k0]if r['side']==2 else k0
    require(k==expect and 0<=k<136,rid+' P2 mapping '+str((a,k,expect)));legal.add(k)
   require(abs(math.fsum(r['pi136'])-1)<1e-12,rid+' pi sum');require(all(math.isfinite(p)and p>=0 and(abs(p-n/63)<1e-14)and(k in legal or(p==0 and n==0))for k,(p,n)in enumerate(zip(r['pi136'],r['visits136']))),rid+' pi visits/mask')
   require(r['action209']in r['legal_order209'],rid+' chosen legal');require(r['tau']==(1 if r['new_ply']<16 else 0),rid+' temperature')
   if r['tau']==0:
    chosen=max(r['mapping136'],key=lambda ak:r['visits136'][ak[1]])[0];require(r['action209']==chosen,rid+' argmax tie/order')
   require(len(r['features648_bits'])==648 and len(r['NN137_bits'])==137,rid+' tensor');require(all(math.isfinite(f32(v))for v in r['features648_bits']+r['NN137_bits']),rid+' finite');require(f32(r['NN137_bits'][-1])==r['rootNN'],rid+' rootNN bits');require(abs(r['rootNN'])<=1 and abs(r['rootmean'])<=1,rid+' value range');require(r['rootNN_view']==r['rootmean_view']=='root side-to-move',rid+' root view')
   z=1 if g['winner']==1 else-1;require(g['status']=='GOAL' and r['side']in(1,2)and r['z_p1']==z and r['z_stm']==(z if r['side']==1 else-z)and r['value_eligible']and r['policy_eligible']and r['joint_eligible'],rid+' z/qualification');counts[split]+=1
   mask=[int(k in legal)for k in range(136)];keys=[r['state_key'],enc({'position':r['state_key'],'side':r['side'],'ply':r['ply'],'history':sorted(r['history_counts'])}),enc(r['features648_bits']),enc({'features':r['features648_bits'],'legalMask':mask})]
   for group,key in zip(groups,keys):group[key].append((r['game_id'],split))

  rawcount=0
  for core in [2,4,6]:
   rawpath=path/('core'+str(core))/'raw-rows.jsonl'
   if rawpath.exists():
    h=hashlib.sha256();index={r['row_id']:r for r in rows}
    with rawpath.open('rb')as f:
     for line in f:
      h.update(line)
      if not line.strip():continue
      rr=json.loads(line);rawcount+=1;require(rr['row_id']in index,'raw teacher export missing '+rr['row_id']);tr=index[rr['row_id']];require(all(tr[k]==v for k,v in rr.items()if k not in ['z_p1','z_stm','value_eligible']),rr['row_id']+' raw join')
    snap[str(rawpath)]={'SHA256':h.hexdigest(),'bytes':rawpath.stat().st_size}
  require(rawcount==len(rows)==owner['raw_saved_rows'],'raw count '+mode);require(all(sum(r['game_id']==g['game_id']for r in rows)==g['rows']for g in games),'game row joins '+mode);statuses=collections.Counter(g['status']for g in games);quality_status.update(statuses);require(dict(statuses)==owner['status_counts'],'status summary '+mode);require(NN==owner['NN_completed_on_eligible_rows']and terminal==owner['terminal_noNN'],'counter summary '+mode);require(len(rows)==owner['Rpolicy']==owner['Rz']==owner['Rjoint'],'eligibility summary '+mode)
  overlap={}
  for name,group in zip(['position','fullstate','features','features_legal'],groups):
   c=[v for v in group.values()if len(set(g for g,s in v))>1];tv=[v for v in c if len(set(s for g,s in v))>1];overlap[name]={'unique':len(group),'crossgame_shared_keys':len(c),'crossgame_row_occurrences':sum(map(len,c)),'train_val_shared_keys':len(tv),'train_val_row_occurrences':sum(map(len,tv))};require(all(owner['overlaps'][name][k]==v for k,v in overlap[name].items()),'overlap '+mode+name)
  batches=None
  if mode.startswith('GPU'):
   broker=load(path/'broker.json');stat=broker['stats'];hist=stat['batch_histogram'];n=sum(hist);samples=sum(i*c for i,c in enumerate(hist));require(n==broker['providerCost']['batches']==rawresult['providerStop']['calls']['cuda'],'batch calls '+mode);require(samples==NN==stat['started']==stat['returned']==stat['resumed']==rawresult['NN']==rawresult['providerStop']['rows']['cuda'],'sample sum '+mode);require(stat['discarded']==stat['rejected_queued']==0,'discard counters '+mode);batches={'histogram':hist,'batch_calls':n,'sample_rows':samples,'effective_batch':samples/n,'full_batch_fraction':hist[8]/n,'mean_queue_ms':stat['queue_ms_sum']/samples,'max_queue_ms':stat['queue_ms_max'],'provider_pipe_ms':stat['provider_pipe_ms'],'provider_stage_spans':broker['providerCost'],'coldinit_s':rawresult['providerStop']['coldinit_s'],'VRAM_peak_reserved_B':rawresult['providerStop']['GPU_peak_reserved_B'],'provider_exit':rawresult['providerStop']['exit'],'max_pending_games':stat['max_pending_games']}
  require(all(not any(v for v in x['zero'].values())and x['exit']['code']==0 for x in rawresult['closed']),'worker closed '+mode);require(sum(x['usedNN']for x in rawresult['closed'])==rawresult['NN'],'worker NN '+mode);wall=proc['jobwall_seconds'];require(wall==owner['allattempt_jobwall_s'],'mode wall '+mode)
  matching={'paired_saved_rows':0,'same_position_action_visits':0,'NN137_maxabs':0,'rootmean_maxabs':0}
  for r in rows:
   key=(r['game_id'],r['ply'])
   if mode=='CPUJS':baseline[key]={k:r[k]for k in ['state_key','action209','visits136','NN137_bits','rootmean']}
   elif key in baseline:
    ref=baseline[key];matching['paired_saved_rows']+=1;matching['same_position_action_visits']+=int(all(r[k]==ref[k]for k in ['state_key','action209','visits136']));matching['NN137_maxabs']=max(matching['NN137_maxabs'],max(abs(f32(a)-f32(b))for a,b in zip(r['NN137_bits'],ref['NN137_bits'])));matching['rootmean_maxabs']=max(matching['rootmean_maxabs'],abs(r['rootmean']-ref['rootmean']))
  dist=[{'game':g['game_id'],'status':g['status'],'winner':g.get('winner'),'total_ply':g.get('plies'),'new_rows':g['rows'],'split':g['split']}for g in games];unknown=sum(g['status']not in ['GOAL','DRAW200','DRAW_NOLEGAL']for g in games);plys=[g['plies']for g in games if g.get('plies')is not None]
  outputs.append({'mode':mode,'all24_status':dict(statuses),'allgame_unknown':unknown,'Rpolicy':len(rows),'Rz':len(rows),'Rjoint':len(rows),'allattempt_jobwall_s':wall,'joint_per_s':len(rows)/wall,'successful_games_per_s':(24-unknown)/wall,'split_rows':dict(counts),'NN_completed_qualified':NN,'NN_actual_attempt':rawresult['NN'],'terminal_noNN':terminal,'NN_discarded':sum(r['NN_discarded']for r in rows),'startup':rawresult['startup_NN'],'finalCP_saved_counter':None,'finalCP_source_once':True,'P2_jump_entries':p2jump,'P2_wall_entries':p2wall,'overlaps':overlap,'all24_distribution':dist,'total_ply_min_median_max':None if not plys else[min(plys),statistics.median(plys),max(plys)],'newply_sum':sum(g['rows']for g in games),'batches':batches,'RAM_peak_sampled':proc['peak_aggregate_RSS'],'exit':proc['exit'],'primary':rawresult['primary'],'point_stopped':not proc['remaining'],'matched_CPUJS':matching,'closed_worker_API_ms':sum(x.get('API_ms',0)for x in rawresult['closed']),'closed_worker_pipe_ms':sum(x.get('pipe_ms',0)for x in rawresult['closed']),'bridge':{k:sum((x.get('bridge')or{}).get(k,0)for x in rawresult['closed'])for k in ['calls','request_bytes','response_bytes']}});totalrows+=len(rows);del rows;gc.collect()
 attempts=[]
 for path in sorted(B.glob('*/process.json')):
  p=load(path);require(not p['remaining'],'allattempt stop '+p['run']);attempts.append({'run':p['run'],'kind':p['kind'],'jobwall':p['jobwall_seconds'],'exit':p['exit'],'reason':p['stop_reason'],'source_git':p['source_git'],'tracked_identities':len(p['tracked'])})
 totalwall=sum(a['jobwall']for a in attempts);require(len(outputs)==5 and sum(quality_status.values())==120,'all120');result.update({'supported':True,'modes':outputs,'all120_status':dict(quality_status),'all_produced_qualified_rows':totalrows,'allattempts':attempts,'allattempt_jobwall_s':totalwall,'repeated_family_rows_per_allattempt_s':totalrows/totalwall,'distinct_sibling_workload_warning':True,'snapshots':snap,'RustCPU_quality':'0 certified rows; all24 unknown/notstarted; failure is checker not NN negative','no_old173_reads':True})
except BaseException as e:result.update({'supported':False,'first_difference':str(e),'failure_type':type(e).__name__,'trace':traceback.format_exc(),'snapshots':snap})
result.update({'elapsed_seconds':time.monotonic()-start,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid()});D.joinpath('arithmetic.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['modes','snapshots','trace','allattempts']}));require(result['supported'],'checker failure is not original science negative')
