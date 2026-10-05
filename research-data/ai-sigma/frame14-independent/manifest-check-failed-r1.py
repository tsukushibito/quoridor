"""Independent label-free arithmetic. No owner calculator, model, or label file imports."""
import pathlib,json,gzip,hashlib,struct,math,collections,time,datetime,os,resource,traceback
os.sched_setaffinity(0,{0});start=time.monotonic();D=pathlib.Path('research-data/ai-sigma/frame14-independent');A=pathlib.Path('research-data/ai-sigma/frame14-teachers/final-qf1-v2');snap={};out={'issue':'quoridor-4lc.196','model_forward':0,'test_labels_raw_preview_statejournal_read':False,'first_difference':None}
def read(p):
 p=pathlib.Path(p);b=p.read_bytes();snap[str(p)]={'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def load(p):return json.loads(read(p))
def require(ok,msg):
 if not ok:raise AssertionError(msg)
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def canonical(r):
 p=r['side']-1;return ['QF1-f32-STM-v1',sorted(r['ids'][p]),sorted(r['ids'][1-p]),[struct.unpack('<I',struct.pack('<f',d))[0]for d in r['distance']]]
def walls_and_distances(key):
 parts=key.split('|');require(len(parts)==5,'state key schema');pawns=[tuple(map(int,p.split(',')))for p in parts[:2]];turn=int(parts[2]);walls=[[] if not part else [tuple(map(int,w.split(',')))for w in part.split(';')]for part in parts[3:]]
 return pawns,turn,walls
distance_cache={}
def distances(walls,pawns):
 h,v=walls;key=(tuple(sorted(h)),tuple(sorted(v)))
 if key not in distance_cache:
  blocked=set()
  for x,y in h:
   for nx in [x,x+1]:blocked.add(frozenset((9*y+nx,9*(y+1)+nx)))
  for x,y in v:
   for ny in [y,y+1]:blocked.add(frozenset((9*ny+x,9*ny+x+1)))
  maps=[]
  for goal in [8,0]:
   dd=[-1]*81;queue=[9*goal+x for x in range(9)]
   for q in queue:dd[q]=0
   for q in queue:
    x,y=q%9,q//9
    for nx,ny in [(x,y+1),(x,y-1),(x+1,y),(x-1,y)]:
     if 0<=nx<9 and 0<=ny<9:
      z=ny*9+nx
      if dd[z]<0 and frozenset((q,z))not in blocked:dd[z]=dd[q]+1;queue.append(z)
   maps.append(dd)
  distance_cache[key]=maps
 return [distance_cache[key][i][9*pawns[i][1]+pawns[i][0]]for i in range(2)]
try:
 meta_bytes=read(A/'all144-metadata.jsonl.gz');mask_bytes=read(A/'fixed-exposure-mask.json');require(hashlib.sha256(meta_bytes).hexdigest()=='1c257a5e440ac50096b56f033ff4e3e183594651d4162e0358326b3f08cf08b1','metadata version not fixed');require(hashlib.sha256(mask_bytes).hexdigest()=='10b502cd9e1c5334e56a3f460ef3edff7f822c8f52f69c3af53529c67c45d5f5','mask version not fixed')
 rows=[json.loads(line)for line in gzip.decompress(meta_bytes).splitlines()if line.strip()];mask=json.loads(mask_bytes);manifest=load(A/'dataset-manifest.json');openings=load('research-data/ai-sigma/frame14-teachers/openings.json');quantity=load('research-data/ai-sigma/frame14-learning/quantity-preregister.json');plan={g['game_id']:g for g in openings['games']};declared={g['game_id']:g for g in manifest['all144_games']}
 require(len(plan)==len(declared)==144 and set(plan)==set(declared),'all144 planned/declared');require(len(rows)==6996,'row denominator')
 require(manifest['metadata_sha256']==snap[str(A/'all144-metadata.jsonl.gz')]['SHA256']==mask['metadata_sha256'],'meta binding');require(manifest['mask_sha256']==snap[str(A/'fixed-exposure-mask.json')]['SHA256'],'mask binding');require(mask['planned_openings_sha256']==snap['research-data/ai-sigma/frame14-teachers/openings.json']['SHA256'],'openings binding')
 allowed={'id','game_id','group','split','train_slot','cohort','opening_ply','ply','state_key','history_key','side','ids','distance','QF1_input_sha256','featureSHA','family'};seen=set();groups={};game_rows=collections.defaultdict(list);net_signatures={};by_split=collections.Counter();wall_feature_checks=distance_checks=0
 for r in rows:
  rid=r['id'];require(set(r)<=allowed,'unexpected field, abort before analysis '+rid);require(rid not in seen,'duplicate row '+rid);seen.add(rid);g=plan[r['game_id']];game_rows[r['game_id']].append(r);s=r['split'];by_split[s]+=1
  require(r['family']==r['group']==g['family']and s==g['split'],'family/partition '+rid);require(groups.setdefault(r['group'],s)==s,'family cross split');require(r['train_slot']==(g['partition_slot']if s=='train' else None),'train ordinal');require(r['opening_ply']==g['target_ply']==len(g['opening']['legal_prefix'])and r['cohort']=='opening-'+str(g['target_ply']),'opening strata');require(r['side']in [1,2]and isinstance(r['ply'],int),'side/ply');require(r['ply']>=r['opening_ply'],'ply range');require(len(r['ids'])==2 and len(r['distance'])==2,'tensor shape');require(all(math.isfinite(v)and 0<=v<=1 for v in r['distance']),'distance bounded')
  pawns,turn,walls=walls_and_distances(r['state_key']);require(turn+1==r['side']and r['ply']%2==turn,'state/side/ply');require(all(0<=x<9 and 0<=y<9 for x,y in pawns),'pawn coordinates');require(all(0<=x<8 and 0<=y<8 for ww in walls for x,y in ww),'wall coordinates')
  remaining=[]
  for view,ids in enumerate(r['ids']):
   require(ids==sorted(set(ids))and 4<=len(ids)<=24 and all(isinstance(i,int)and 0<=i<312 for i in ids),'sparse feature shape '+rid);rot=view==1;me=pawns[view];op=pawns[1-view];square=lambda q:80-(9*q[1]+q[0])if rot else 9*q[1]+q[0];expected=[square(me),81+square(op)]
   for ww,base in zip(walls,[162,226]):
    expected.extend(base+(63-(8*y+x)if rot else 8*y+x)for x,y in ww)
   remme=[i-290 for i in ids if 290<=i<=300];remop=[i-301 for i in ids if 301<=i<=311];require(len(remme)==len(remop)==1,'wall remaining feature ids');remaining.append([remme[0],remop[0]]);expected.extend([290+remme[0],301+remop[0]]);require(sorted(expected)==ids,'spatial wall/rotation features '+rid);wall_feature_checks+=1
  require(remaining[0]==list(reversed(remaining[1])),'paired remaining wall views');require(sum(remaining[0])+sum(len(w)for w in walls)==20,'wall conservation')
  dd=distances(walls,pawns);require(all(d>=0 for d in dd),'distance reachability');expected=[d/80 for d in(dd if r['side']==1 else reversed(dd))];require(all(struct.pack('<f',a)==struct.pack('<f',b)for a,b in zip(expected,r['distance'])),'independent graph distance '+rid);distance_checks+=1
  sig=digest(canonical(r));require(sig==r['QF1_input_sha256']==r['featureSHA'],'actual model signature '+rid);require(len(r['history_key'])==64 and all(c in '0123456789abcdef'for c in r['history_key']),'history hash shape');net_signatures[rid]=sig
 require(dict(by_split)=={'train':4653,'validation':1248,'test':1095},'split row counts');require(set(seen)==set(mask['rows']),'mask all-row denominator');require(len(groups)==144,'family count')
 require(collections.Counter(g['split']for g in plan.values())=={'train':96,'validation':24,'test':24},'split planned games');require(len(set(g['family']for g in plan.values()))==144,'family reused across slots')
 train_plan=sorted((g for g in plan.values()if g['split']=='train'),key=lambda g:g['partition_slot']);require([g['partition_slot']for g in train_plan]==list(range(1,97)),'all96 ordered');require(mask['planned_train_groups']==[g['family']for g in train_plan],'maximum96 planned ordering')
 def sigset(rr):return [set(r[k]for r in rr)for k in ['state_key','history_key']]+[set(net_signatures[r['id']]for r in rr)]
 train=[r for r in rows if r['split']=='train'];val=[r for r in rows if r['split']=='validation'];tr=sigset(train);tv=sigset(train+val);exclusions=collections.Counter();allgames=[];eligible_counts=collections.Counter();total_counts=collections.Counter();mask_math=[];maskgames={}
 for gid,g in plan.items():
  rr=game_rows[gid];require(rr,'planned game absent in label-free row manifest');require([r['ply']for r in rr]==list(range(g['target_ply'],g['target_ply']+len(rr))),'contiguous ply '+gid);require(rr[0]['state_key']==g['opening']['key']and rr[0]['side']==g['opening']['side'],'opening firststate')
  # Only the first opening history is available label-free; later history is opaque.
  history=sorted(g['opening']['root_state']['history'],key=lambda kv:kv[0]);require(digest([rr[0]['state_key'],history])==rr[0]['history_key'],'opening history signature '+gid)
  elig=0;reasons=collections.Counter()
  for r in rr:
   s=r['split'];refs=tr if s=='validation' else tv;shared=[]if s=='train' else sorted(name for name,key,seenkeys in zip(['state','history','QF1'],[r['state_key'],r['history_key'],net_signatures[r['id']]],refs)if key in seenkeys);want={'primary_eligible':not shared,'exposure':shared,'split':s,'group':r['group']};require(mask['rows'][r['id']]==want,'independent OR mask '+r['id']);elig+=not shared
   for why in shared:reasons[why]+=1;exclusions[s+':'+why]+=1
   mask_math.append([r['id'],want])
  s=g['split'];eligible_counts[s]+=elig;total_counts[s]+=len(rr);decl=declared[gid];require(decl=={'game_id':gid,'group':g['family'],'split':s,'train_slot':g['partition_slot']if s=='train'else None,'status':'GOAL','all_rows':len(rr),'eligible_rows':elig,'eligible_zero':elig==0},'aggregate allgame declaration '+gid);maskgames[g['family']]={'split':s,'rows':len(rr),'eligible':elig};allgames.append({'game_id':gid,'group':g['family'],'split':s,'all_rows':len(rr),'eligible_rows':elig,'removed_rows':len(rr)-elig,'reasons':dict(reasons),'opening_ply':g['target_ply']})
 require(mask['games']==maskgames,'allgame mask counts');require(mask['zero_eligible_games']==sorted(g for g,v in maskgames.items()if not v['eligible']),'zero eligible denominator');require(mask['labels_used']is False,'mask receipt labels false')
 nested={}
 for n in [24,48,96]:
  chosen=train_plan[:n];counts=collections.Counter(g['target_ply']for g in chosen);require(counts=={d:n//6 for d in [8,12,16,20,24,28]},'nested strata'+str(n));nested[str(n)]={'games':n,'rows':sum(len(game_rows[g['game_id']])for g in chosen),'openings':dict(counts),'groups_SHA256':digest([g['family']for g in chosen]),'validation_same_mask_SHA256':manifest['mask_sha256']}
 for s in ['validation','test']:require(collections.Counter(g['target_ply']for g in plan.values()if g['split']==s)=={d:4 for d in [8,12,16,20,24,28]},'val/test opening balance')
 source={}
 for p,expected in manifest['shared_interface']['source'].items():
  sha=hashlib.sha256(read(p)).hexdigest();require(sha==expected,'shared frozen source mismatch '+p);source[p]=sha
 # Detect producer mutation across the arithmetic pass; no label path dereference.
 for p,entry in list(snap.items()):require(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==entry['SHA256'],'read version changed '+p)
 out.update({'supported_label_free_arithmetic':True,'all_planned_games':144,'manifest_claim_GOAL_games':144,'raw_terminal_quality_independently_checked':False,'all_rows':len(rows),'rows_by_split':dict(total_counts),'eligible_rows_by_split':dict(eligible_counts),'excluded_rows_by_split':{s:total_counts[s]-eligible_counts[s]for s in total_counts},'zero_eligible_games':mask['zero_eligible_games'],'positive_eligible_games':{s:sum(g['split']==s and g['eligible_rows']>0 for g in allgames)for s in total_counts},'exposure_reason_counts_nonexclusive':dict(exclusions),'allgame_denominators':allgames,'nested_train':nested,'independent_QF1_spatial_views_checked':wall_feature_checks,'independent_graph_distances_checked':distance_checks,'remaining_wall_ownership_from_raw':False,'later_history_truth_checked':False,'first_opening_history_checked':144,'independent_mask_math_SHA256':digest(sorted(mask_math)),'source_bindings':source,'quantity_preregister_snapshot':quantity,'sealed_test_reference_only':{'path':manifest['test_labels'],'SHA256':manifest['test_labels_sha256']},'candidate_freeze_and_testreceipt_pending':True})
except BaseException as e:out.update({'supported_label_free_arithmetic':False,'first_difference':str(e),'failure_type':type(e).__name__,'trace':traceback.format_exc()})
out.update({'snapshots':snap,'wall_s':time.monotonic()-start,'RSS_B':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid(),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()});D.joinpath('manifest-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['supported_label_free_arithmetic','first_difference','wall_s','RSS_B','PID','UTC']}));require(out['supported_label_free_arithmetic'],'critic checker difference; not original science negative')
