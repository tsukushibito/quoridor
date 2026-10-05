import pathlib,json,gzip,hashlib,struct,math,time,datetime,resource,os,collections,traceback
os.sched_setaffinity(0,{0});D=pathlib.Path('research-data/ai-sigma/179-native-teacher-independent');A=pathlib.Path('research-data/ai-sigma/176-native-teacher-pipeline');start=time.monotonic();result={'issue':'quoridor-4lc.179','NN':0,'start':datetime.datetime.now(datetime.timezone.utc).isoformat(),'first_difference':None}
def load(n):return json.loads((A/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return json.dumps(x,separators=(',',':'))
def require(v,msg):
 if not v:raise AssertionError(msg)
def f32(b):return struct.unpack('<f',struct.pack('<I',b))[0]
try:
 rows=[json.loads(l)for l in gzip.open(A/'teacher-rows.jsonl.gz','rt')];games=load('all-game-status.json');G={g['game_id']:g for g in games};specs={g['game_id']:g for g in load('openings.json')['games']};seen=set();groups=[collections.defaultdict(list)for _ in range(4)];directions=[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)];flip=[1,0,2,3,6,7,4,5];p2jump=p2wall=0;counts=collections.Counter();NN=terminal=CP=0
 for r in rows:
  rid=r['row_id'];require(rid not in seen,rid+' duplicate');seen.add(rid);g=G[r['game_id']];s=specs[r['game_id']];require(r['lineage']==g['lineage']==s['lineage'],rid+' lineage');split='validation'if int(hashlib.sha256(r['lineage'].encode()).hexdigest()[:8],16)%5==0 else'train';require(r['split']==split==s['split'],rid+' split');require(r['lineage'].startswith('native176-train-')and'173'not in r['lineage'],rid+' holdout domain')
  require(r['rootN']==64 and r['edgeSum']==63,rid+' K');require(r['NN_completed']+r['terminal_noNN']==64 and r['NN_discarded']==0,rid+' NN');NN+=r['NN_completed'];terminal+=r['terminal_noNN'];CP+=r['CP_received'];require(r['CP_received']==1,rid+' finalCP')
  require(len(r['visits136'])==len(r['pi136'])==136 and sum(r['visits136'])==63,rid+' visits');require(all(isinstance(v,int)and v>=0 for v in r['visits136']),rid+' noninteger visits');require(len(r['mapping136'])==len(r['legal_order209'])and [a for a,k in r['mapping136']]==r['legal_order209'],rid+' order');require(len(set(a for a,k in r['mapping136']))==len(r['mapping136'])and len(set(k for a,k in r['mapping136']))==len(r['mapping136']),rid+' mask injectivity')
  parts=r['state_key'].split('|');pawn=list(map(int,parts[r['side']-1].split(',')));opp=list(map(int,parts[2-r['side']].split(',')));legal=set()
  for a,k in r['mapping136']:
   if a>=81:
    v=a>=145;offset=145 if v else81;x=(a-offset)%8;y=(a-offset)//8;expect=8+(64 if v else0)+8*(7-y if r['side']==2 else y)+x;p2wall+=int(r['side']==2)
   else:
    dest=[a%9,a//9];dx=dest[0]-pawn[0];dy=dest[1]-pawn[1]
    if abs(dx)==2 or abs(dy)==2:dx//=2;dy//=2;p2jump+=int(r['side']==2)
    require((dx,dy)in directions,rid+' destination');k0=directions.index((dx,dy));expect=flip[k0]if r['side']==2 else k0
   require(k==expect and 0<=k<136,rid+' P2 mapping '+str((a,k,expect)));legal.add(k)
  require(abs(math.fsum(r['pi136'])-1)<1e-12,rid+' pi sum');require(all(math.isfinite(p)and p>=0 and(abs(p-n/63)<1e-14)and(k in legal or(p==0 and n==0))for k,(p,n)in enumerate(zip(r['pi136'],r['visits136']))),rid+' pi visits/mask')
  require(r['action209']in r['legal_order209'],rid+' chosen legal');require(r['tau']==(1 if r['new_ply']<16 else0),rid+' temperature')
  if r['tau']==0:
   chosen=max(r['mapping136'],key=lambda ak:r['visits136'][ak[1]])[0];require(r['action209']==chosen,rid+' argmax tie/order')
  require(len(r['features648_bits'])==648 and len(r['NN137_bits'])==137,rid+' tensor');require(all(math.isfinite(f32(v))for v in r['features648_bits']+r['NN137_bits']),rid+' finite');require(f32(r['NN137_bits'][-1])==r['rootNN'],rid+' rootNN bits');require(abs(r['rootNN'])<=1 and abs(r['rootmean'])<=1,rid+' value range');require(r['rootNN_view']==r['rootmean_view']=='root side-to-move',rid+' root view')
  z=1 if g['winner']==1 else-1;require(g['status']=='GOAL' and r['side']in(1,2)and r['z_p1']==z and r['z_stm']==(z if r['side']==1 else-z)and r['value_eligible']and r['policy_eligible']and r['joint_eligible'],rid+' z/qualification');counts[split]+=1
  mask=[int(k in legal)for k in range(136)];keys=[r['state_key'],enc({'position':r['state_key'],'side':r['side'],'ply':r['ply'],'history':sorted(r['history_counts'])}),enc(r['features648_bits']),enc({'features':r['features648_bits'],'legalMask':mask})]
  for group,key in zip(groups,keys):group[key].append((r['game_id'],split))
 require(len(rows)==1409 and len(games)==len(specs)==24,'planned rows/games');require(all(sum(r['game_id']==g['game_id']for r in rows)==g['rows']for g in games),'all game rows')
 overlaps={}
 for name,group in zip(['position_key','full_state_history_side_ply','features648_only','features648_plus_legalmask136'],groups):
  cross=[v for v in group.values()if len(set(g for g,s in v))>1];tv=[v for v in cross if len(set(s for g,s in v))>1];o={'unique':len(group),'crossgame_shared_keys':len(cross),'crossgame_shared_row_occurrences':sum(map(len,cross)),'train_validation_shared_keys':len(tv),'train_validation_shared_row_occurrences':sum(map(len,tv))};require(all(load('overlap-detail.json')[name][k]==v for k,v in o.items()),name+' owner overlap');overlaps[name]=o
 pr=load('learner-preregister.json');tr=load('learner-training.json');ex=load('learner-export.json');rr=load('learner-reload.json');require(sha(A/'teacher-rows.jsonl.gz')==pr['dataset_SHA256']==tr['dataset_SHA256']==load('dataset-summary.json')['dataset_SHA256'],'datasetSHA');require(sha(A/'student-checkpoint.pt')==tr['checkpoint_SHA256'],'checkpointSHA');require(sha(A/'student.onnx')==ex['ONNX_SHA256'],'ONNXSHA');require([rows[i]['row_id']for i in pr['parity_indices']]==pr['parity_row_ids']==rr['row_ids']==ex['row_ids'],'five rows');require(sha(pathlib.Path('tools/ai-sigma-native-teacher-pipeline/learn.py'))==pr['source']['tools/ai-sigma-native-teacher-pipeline/learn.py'],'learner sourceSHA');require(tr['steps']==200 and tr['rootmean_auxiliary_weight']==0 and tr['train_rows']==counts['train']and tr['validation_rows']==counts['validation'],'learnersettings')
 costs=load('cost-ledger.json');process=[];phase=collections.Counter();base=pathlib.Path('.artifacts/ai-sigma/resume-20261003/NATIVE-TEACHER-PIPELINE/runs')
 for a in costs['all_attempts']:
  if a.get('wall_seconds')is None:process.append({'run':a['run'],'wall':None,'NN':a['NN'],'typed':a['typed']['error']});continue
  p=json.loads((base/(a['run']+'.process.json')).read_text());sec=(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds();require(abs(sec-a['wall_seconds'])<1e-9,a['run']+' cost');require(not p['remaining']and not p['unknown_adopted'],a['run']+' stopped');phase[a['phase']]+=sec;process.append({'run':a['run'],'wall':sec,'exit':p['exit'],'stop_reason':p['stop_reason']})
 require(abs(sum(phase.values())-costs['all_owned_compute_jobwall_seconds'])<1e-8,'allattemptcost');arena=load('arena-results.json');require(len(arena['slots'])==arena['planned_games']==4 and all(s['status']=='GOAL'and s['score']==0 and s['winner']!=s['student_side']and s['lineage'].startswith('native176-eval-')for s in arena['slots']),'arena all4');require(arena['primary']is None and arena['monitor_state']=='READY'and all(c['exit']['code']==0 for c in arena['closed']),'arena stop')
 result.update({'supported':True,'rows':len(rows),'games':len(games),'split_rows':dict(counts),'split_games':dict(collections.Counter(g['split']for g in games)),'Rpolicy':1409,'Rz':1409,'Rjoint':1409,'NN':NN,'terminal_noNN':terminal,'CP':CP,'P2_jump_mapping_entries':p2jump,'P2_wall_mapping_entries':p2wall,'overlaps':overlaps,'learner_saved_receipts_only':True,'binary_hashes':{'dataset':sha(A/'teacher-rows.jsonl.gz'),'checkpoint':sha(A/'student-checkpoint.pt'),'ONNX':sha(A/'student.onnx')},'processes':process,'phase_jobwall':dict(phase),'all_compute_wall':sum(phase.values()),'production_rate':1409/phase['generate'],'known_compute_export_overlap_wall':sum(phase.values())+costs['export_seconds']+costs['finite_overlap_checker_seconds'],'arena_WDL':[0,0,4],'GPU_generation_rate_unestablished':True})
except BaseException as e:result.update({'supported':False,'first_difference':str(e),'failure_type':type(e).__name__,'trace':traceback.format_exc()})
result.update({'elapsed_seconds':time.monotonic()-start,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid()});(D/'arithmetic.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['processes','binary_hashes','overlaps','trace']}));require(result['supported'],'checker needs repair; not original science negative')
