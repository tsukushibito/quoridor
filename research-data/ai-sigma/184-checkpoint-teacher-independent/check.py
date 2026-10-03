import pathlib,json,gzip,hashlib,struct,math,time,datetime,resource,os,collections,traceback
os.sched_setaffinity(0,{0});D=pathlib.Path('research-data/ai-sigma/184-checkpoint-teacher-independent');A=pathlib.Path('research-data/ai-sigma/181-checkpoint-teacher');start=time.monotonic();result={'issue':'quoridor-4lc.184','NN':0,'start':datetime.datetime.now(datetime.timezone.utc).isoformat(),'first_difference':None}
def load(n):return json.loads((A/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return json.dumps(x,separators=(',',':'))
def require(v,msg):
 if not v:raise AssertionError(msg)
def f32(b):return struct.unpack('<f',struct.pack('<I',b))[0]
try:
 rows=[json.loads(l)for l in gzip.open(A/'teacher-rows.jsonl.gz','rt')];games=load('all-game-status.json');G={g['game_id']:g for g in games};specs={g['game_id']:g for g in load('openings.json')['games']};seen=set();groups=[collections.defaultdict(list)for _ in range(4)];directions=[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)];flip=[1,0,2,3,6,7,4,5];p2jump=p2wall=0;counts=collections.Counter();NN=terminal=CP=0
 for r in rows:
  rid=r['row_id'];require(rid not in seen,rid+' duplicate');seen.add(rid);g=G[r['game_id']];s=specs[r['game_id']];require(r['lineage']==g['lineage']==s['lineage'],rid+' lineage');split=s['split'];require(s['split_hash']==hashlib.sha256(('NATIVE181_SPLIT_V1|'+r['lineage']).encode()).hexdigest(),rid+' split hash');require(r['split']==split==s['split'],rid+' split');require(r['lineage'].startswith('native181-train-')and'173'not in r['lineage'],rid+' holdout domain')
  require(r['rootN']==64 and r['edgeSum']==63,rid+' K');require(r['NN_completed']+r['terminal_noNN']==64 and r['NN_discarded']==0,rid+' NN');NN+=r['NN_completed'];terminal+=r['terminal_noNN'];CP+=r['CP_received'];require(r['CP_received']==1,rid+' finalCP')
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
 require(len(rows)==1353 and len(games)==len(specs)==24,'planned rows/games');require(all(sum(r['game_id']==g['game_id']for r in rows)==g['rows']for g in games),'all game rows')
 overlaps={}
 for name,group in zip(['position_key','full_state_history_side_ply','features648_only','features648_plus_legalmask136'],groups):
  cross=[v for v in group.values()if len(set(g for g,s in v))>1];tv=[v for v in cross if len(set(s for g,s in v))>1];o={'unique':len(group),'crossgame_shared_keys':len(cross),'crossgame_shared_row_occurrences':sum(map(len,cross)),'train_validation_shared_keys':len(tv),'train_validation_shared_row_occurrences':sum(map(len,tv))};require(all(load('overlap-detail.json')[name][k]==v for k,v in o.items()),name+' owner overlap');overlaps[name]=o

 ranked=sorted(specs.values(),key=lambda s:s['split_hash']);require(all(s['split']==('validation'if s in ranked[:4]else'train')for s in ranked),'family rank')
 conn=[json.loads(l)for l in gzip.open(A/'training-connection-rows.jsonl.gz','rt')];newconn=[r for r in conn if r['lineage'].startswith('native181-train-')];require(newconn==rows,'connection newrows exact');require(all(r['lineage'].startswith(('native181-train-','native176-train-'))for r in conn),'allowed lineage');require(len(set(r['row_id']for r in conn))==len(conn),'connection duplicate');cc=collections.Counter(('new'if r['lineage'].startswith('native181-')else'old',r['split'])for r in conn);require(dict(cc)=={('old','train'):1188,('old','validation'):221,('new','train'):1072,('new','validation'):281},'connection counts')
 crossgroups=[collections.defaultdict(list)for _ in range(4)]
 for r in conn:
  mask=[int(k in set(k for a,k in r['mapping136']))for k in range(136)];keys=[r['state_key'],enc({'position':r['state_key'],'side':r['side'],'ply':r['ply'],'history':sorted(r['history_counts'])}),enc(r['features648_bits']),enc({'features':r['features648_bits'],'legalMask':mask})]
  for group,key in zip(crossgroups,keys):group[key].append((r['game_id'],r['split'],'new'if r['lineage'].startswith('native181-')else'old'))
 cross={}
 for name,group in zip(overlaps,crossgroups):
  c=[v for v in group.values()if len(set(x[0]for x in v))>1];tv=[v for v in group.values()if len(set(x[1]for x in v))>1];on=[v for v in group.values()if len(set(x[2]for x in v))>1];cross[name]={'unique':len(group),'crossgame_keys':len(c),'crossgame_occ':sum(map(len,c)),'train_validation_keys':len(tv),'train_validation_occ':sum(map(len,tv)),'old_new_shared_keys':len(on),'old_new_shared_occ':sum(map(len,on))};require(cross[name]==load('learner-cross-overlap.json')['definitions'][name],'cross '+name)
 pr=load('learner-preregister.json');tr=load('learner-training.json');ex=load('learner-export.json');rr=load('learner-reload.json')
 require(sha(A/'teacher-rows.jsonl.gz')==pr['new_dataset_SHA256']==load('dataset-summary.json')['dataset_SHA256'],'new dataset hash');require(sha(A/'training-connection-rows.jsonl.gz')==pr['dataset_SHA256']==tr['dataset_SHA256'],'connection hash');require(sha(A/'student-checkpoint.pt')==tr['checkpoint_SHA256'],'checkpoint hash');require(sha(A/'student.onnx')==ex['ONNX_SHA256'],'ONNX hash');require(sha(pathlib.Path('research-data/ai-sigma/176-native-teacher-pipeline/student-checkpoint.pt'))==pr['parent_checkpoint_SHA256']==tr['continuation_parent_checkpoint_SHA256'],'parent hash');require([conn[i]['row_id']for i in pr['parity_indices']]==pr['parity_row_ids']==ex['row_ids']==rr['row_ids'],'fixed five rows')
 require(tr['steps']==pr['steps']==200 and tr['train_rows']==2260 and tr['validation_rows']==502 and tr['rootmean_auxiliary_weight']==0,'learner conditions');loss={}
 for name,b in tr['loss_before'].items():
  a=tr['loss_after'][name];require(abs(b[0]-b[1]-b[2])<4e-7 and abs(a[0]-a[1]-a[2])<4e-7,'loss sum '+name);loss[name]={'before':b,'after':a,'delta':[a[i]-b[i]for i in range(3)]}
 valagg={t:[sum(tr[t][g][k]*n for g,n in [('original_validation',221),('new_validation',281)])/502 for k in range(3)]for t in ['loss_before','loss_after']}
 gamez=[{'game':g['game_id'],'split':g['split'],'rows':g['rows'],'winner':g['winner'],'z_stm_counts':dict(collections.Counter(r['z_stm']for r in rows if r['game_id']==g['game_id']))}for g in games]
 import tarfile,statistics
 manifest=load('archive-manifest.json');raw_hashes={}
 with tarfile.open(A/'attemptpack.tar.gz','r:gz')as tar:
  def member(n):
   b=tar.extractfile(n).read();require(hashlib.sha256(b).hexdigest()==manifest['members'][n],'archive member '+n);raw_hashes[n]=manifest['members'][n];return b
  base='.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER/runs/';cost=load('cost-ledger.json');process=[]
  for a in cost['attempts']:
   p=json.loads(member(a['receipt']));sec=(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds();require(abs(sec-a['wall_seconds'])<1e-9,'process cost '+a['run']);require(not p['remaining']and not p.get('unknown_adopted',[]),'process stop '+a['run']);process.append({'run':a['run'],'seconds':sec,'exit':p['exit']})
  measured=[json.loads(l)for l in member(base+'native181-measure-r1/rows.jsonl').splitlines()];require(len(measured)==27,'27 K800 rows');prod=json.loads(member(base+'native181-production-r1/result.json'));result['production_raw_keys']=list(prod)
 total=sum(p['seconds']for p in process);require(abs(total-cost['recorded_all_guardian_jobwall_seconds'])<1e-8,'all guardian sum')
 result.update({'supported':True,'rows':len(rows),'planned_games':len(games),'all_status':dict(collections.Counter(g['status']for g in games)),'split_rows':dict(counts),'split_games':dict(collections.Counter(g['split']for g in games)),'recorded_teacher_NN':NN,'NN_executed':0,'terminal_noNN':terminal,'CP':CP,'P2_jump_entries':p2jump,'P2_wall_entries':p2wall,'overlaps':overlaps,'cross_old_new':cross,'loss':loss,'weighted_combined_validation':valagg,'game_z':gamez,'learner_saved_receipts_only':True,'independent_forward':False,'processes':process,'production_wall':next(p['seconds']for p in process if p['run']=='native181-production-r1'),'all_guardian_wall':total,'production_rate':1353/195.29244,'all_guardian_amortized_rows_per_s':1353/total,'export_seconds':cost['production_export_seconds'],'unknown_prep':True,'raw_member_hashes':raw_hashes,'measurement_row_keys':list(measured[0]),'measurement_scalar_sample':{k:v for k,v in measured[0].items()if not isinstance(v,(list,dict))}})
except BaseException as e:result.update({'supported':False,'first_difference':str(e),'failure_type':type(e).__name__,'trace':traceback.format_exc()})
result.update({'elapsed_seconds':time.monotonic()-start,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid()});(D/'arithmetic.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['raw_member_hashes','game_z','overlaps','cross_old_new','trace']}));require(result['supported'],'checker failure is not original science negative')
