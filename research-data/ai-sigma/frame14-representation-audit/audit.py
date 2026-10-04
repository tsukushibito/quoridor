"""NN0 independent QF1 field witnesses and one train-only weighted distance fit."""
import collections,datetime,gzip,hashlib,json,math,os,pathlib,resource,struct,tarfile,time
os.sched_setaffinity(0,{0});start=time.monotonic()
D=pathlib.Path('research-data/ai-sigma/frame14-representation-audit');P=pathlib.Path('research-data/ai-sigma/frame14-teachers');A=P/'final-qf1-v2';snap={}
def read(p):
 p=pathlib.Path(p);b=p.read_bytes();snap[str(p)]=hashlib.sha256(b).hexdigest();return b
def load(p):return json.loads(read(p))
def gzrows(p):
 p=pathlib.Path(p);snap[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 with gzip.open(p,'rt') as f:
  for l in f:
   if l.strip():yield json.loads(l)
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def avg(v):return math.fsum(v)/len(v)
def eq(a,b):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(a,b)
fixed=load(D/'fixed-witnesses.json');assert all(w['id'] for w in fixed['witnesses'])
metadata=[r for r in gzrows(A/'all144-metadata.jsonl.gz') if r['split'] in ('train','validation')];byid={r['id']:r for r in metadata}
assert len(metadata)==5901 and snap[str(A/'all144-metadata.jsonl.gz')]==fixed['metadata_SHA']
labels=list(gzrows(A/'training-labels.jsonl.gz'));labs={r['id']:r for r in labels};assert set(labs)==set(byid)
mask=load(A/'fixed-exposure-mask.json');specs={g['game_id']:g for g in load(P/'openings.json')['games'] if g['split'] in ('train','validation')}
teachers={};wids={w['id'] for w in fixed['witnesses']};gids={w['game_id'] for w in fixed['witnesses']}
for split in ('train','validation'):
 for r in gzrows(P/(split+'-teacher-rows.jsonl.gz')):
  if r['game_id'] in gids:teachers[r['row_id']]=r
 journals={r['id']:r for r in gzrows(P/(split+'-state-journal.jsonl.gz')) if r['id'] in wids}
 if split=='train':jall=journals
 else:jall.update(journals)
archive=load(P/'archive-manifest.json')['archives']['unsealed'];games={};raw={};member_hashes={}
selected={n for n in archive['members'] if n.endswith('/games.jsonl')}
selected|={n for n in archive['members'] if '/native194-train01-r1/' in n and n.endswith('/raw-rows.jsonl')}
assert not any('test' in n for n in selected)
arc=pathlib.Path(archive['path']);snap[str(arc)]=hashlib.sha256(arc.read_bytes()).hexdigest();assert snap[str(arc)]==archive['SHA256']
with tarfile.open(arc,'r|gz') as tar:
 for member in tar:
  if member.name not in selected:continue
  h=hashlib.sha256();f=tar.extractfile(member)
  for line in f:
   h.update(line);r=json.loads(line)
   if member.name.endswith('/games.jsonl'):
    assert r['split'] in ('train','validation');games[r['game_id']]=r
   elif r['row_id'] in wids:raw[r['row_id']]=r
  member_hashes[member.name]=h.hexdigest();assert h.hexdigest()==archive['members'][member.name]['SHA256']
assert set(games)==set(specs) and set(raw)==wids
def apply(state,a):
 pawns,hw,vw,rem,ply=state;side=ply%2
 if a['type']=='pawn':
  dx,dy=a['direction'];tx,ty=pawns[side][0]+dx,pawns[side][1]+dy
  if (dx==0 or dy==0) and [tx,ty]==pawns[1-side]:tx+=dx;ty+=dy
  pawns[side]=[tx,ty]
 else:
  assert a['type']=='wall'; (hw if a['orientation']=='h' else vw).append((a['x'],a['y']));rem[side]-=1
 state[4]+=1
def make(prefix):
 st=[[[4,0],[4,8]],[],[],[10,10],0]
 for a in prefix:apply(st,a)
 return st
def key(st):
 return '|'.join([','.join(map(str,p)) for p in st[0]]+[str(st[4]%2)]+[';'.join(','.join(map(str,a)) for a in sorted(w)) for w in st[1:3]])
def maps(st):
 blocked=set()
 for x,y in st[1]:
  for xx in (x,x+1):blocked.add(frozenset((9*y+xx,9*(y+1)+xx)))
 for x,y in st[2]:
  for yy in (y,y+1):blocked.add(frozenset((9*yy+x,9*yy+x+1)))
 result=[]
 for goal in (8,0):
  dd=[81]*81;q=[9*goal+x for x in range(9)]
  for i in q:dd[i]=0
  for i in q:
   x,y=i%9,i//9
   for nx,ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
    j=9*ny+nx
    if 0<=nx<9 and 0<=ny<9 and dd[j]==81 and frozenset((i,j)) not in blocked:dd[j]=dd[i]+1;q.append(j)
  result.append(dd)
 return result
def derive(st):
 pawns,hw,vw,rem,ply=st;side=ply%2;mm=maps(st);ids=[]
 for view in (0,1):
  ix=lambda p:80-(9*p[1]+p[0]) if view else 9*p[1]+p[0]
  ii=[ix(pawns[view]),81+ix(pawns[1-view])]
  for walls,base in ((hw,162),(vw,226)):ii.extend(base+(63-(8*y+x) if view else 8*y+x) for x,y in walls)
  ii.extend([290+rem[view],301+rem[1-view]]);ids.append(sorted(ii))
 distances=[mm[v][pawns[v][1]*9+pawns[v][0]]/80 for v in (side,1-side)]
 planes=[[0.0]*81 for _ in range(8)]
 for channel,who in ((0,side),(1,1-side)):
  x,y=pawns[who];planes[channel][(8-y if side else y)*9+x]=1
 for x,y in hw:
  for xx in (x,x+1):planes[2][(7-y if side else y)*9+xx]=1
 for x,y in vw:
  for yy in (y,y+1):planes[3][(8-yy if side else yy)*9+x]=1
 for i in range(81):
  planes[4][i]=rem[side]/10;planes[5][i]=rem[1-side]/10
  source=(8-i//9)*9+i%9 if side else i
  for ch,who in ((6,side),(7,1-side)):planes[ch][i]=min(mm[who][source],80)/80 if mm[who][source]<81 else 1
 return ids,distances,[bits(v) for p in planes for v in p]
witness=[]
for w in fixed['witnesses']:
 m=byid[w['id']];t=teachers[w['id']];r=raw[w['id']];g=specs[w['game_id']];st=make(g['opening']['legal_prefix'])
 preceding=sorted([x for x in teachers.values() if x['game_id']==w['game_id'] and x['ply']<w['ply']],key=lambda x:x['ply'])
 for prev in preceding:assert key(st)==prev['state_key'];apply(st,prev['action'])
 assert st[4]==m['ply'] and key(st)==m['state_key']==t['state_key']==r['state_key']
 ids,ds,nn=derive(st);assert ids==m['ids'];assert [bits(v) for v in ds]==[bits(v) for v in m['distance']]
 assert nn==t['features648_bits']==r['features648_bits']
 assert hashlib.sha256(json.dumps(nn,separators=(',',':')).encode()).hexdigest()==jall[w['id']]['features648SHA']
 canonical=['QF1-f32-STM-v1',ids[m['side']-1],ids[2-m['side']],[bits(v) for v in ds]]
 assert hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()==m['QF1_input_sha256']
 assert t['rootmean_view']==r['rootmean_view']=='root side-to-move';assert t['rootNN_view']=='root side-to-move'
 eq(t['rootmean'],r['rootmean']);eq(labs[w['id']]['rootmean'],r['rootmean']);assert bits(r['rootNN'])==r['NN137_bits'][136]
 z=(1 if games[w['game_id']]['winner']==1 else -1)*(1 if m['side']==1 else -1)
 assert t['z_stm']==labs[w['id']]['z']==z
 witness.append({**w,'PASS':True,'remaining_by_player':st[3],'derived_ids':ids,'STM_distance_f32bits':canonical[3],'canonicalSHA':m['QF1_input_sha256'],'features648SHA':jall[w['id']]['features648SHA'],'rootNN':r['rootNN'],'rootmean':r['rootmean'],'label_rootmean':labs[w['id']]['rootmean'],'leafNN':r['leafNN'],'z_stm':z,'CP_root_sum_unstored':True})
for gid,g in games.items():
 st=make(g['legal_prefix']);assert g['status']=='GOAL' and st[4]==g['plies']
 win=1 if st[0][0][1]==8 else 2 if st[0][1][1]==0 else None;assert win==g['winner']
for m in metadata:
 assert mask['rows'][m['id']]['primary_eligible'];l=labs[m['id']]
 assert l['split']==m['split'];g=games[m['game_id']];z=(1 if g['winner']==1 else -1)*(1 if m['side']==1 else -1);assert l['z']==z
 ds=[f32(v) for v in m['distance']];m['s']=ds[1]-ds[0];m['rootmean']=l['rootmean'];m['z']=l['z']
train=[r for r in metadata if r['split']=='train'];val=[r for r in metadata if r['split']=='validation'];assert len(train)==4653 and len(val)==1248
counts=collections.Counter(r['group'] for r in train);assert len(counts)==96
moment=lambda fn:math.fsum(fn(r)/(96*counts[r['group']]) for r in train)
ms=moment(lambda r:r['s']);my=moment(lambda r:r['rootmean']);var=moment(lambda r:(r['s']-ms)**2);cov=moment(lambda r:(r['s']-ms)*(r['rootmean']-my))
b=cov/var if var else 0;a=my-b*ms
predict=lambda r:max(-1,min(1,a+b*r['s']))
def metrics(rs,fn):
 out={'rows':len(rs),'games':len({r['group'] for r in rs})};gg=collections.defaultdict(list)
 for r in rs:gg[r['group']].append(r)
 for t in ('rootmean','z'):
  out[t+'_row_MSE']=avg([(fn(r)-r[t])**2 for r in rs]);out[t+'_game_MSE']=avg([avg([(fn(r)-r[t])**2 for r in vv]) for vv in gg.values()])
 out['z_sign_row']=avg([fn(r)*r['z']>0 for r in rs]);out['z_sign_game']=avg([avg([fn(r)*r['z']>0 for r in vv]) for vv in gg.values()])
 return out
fit={'a':a,'b':b,'mean_s':ms,'variance_s':var,'covariance_s_rootmean':cov,'constant_train_gameequal':my,'zero_variance':var==0,'rule':'unclipped train-only WLS, then clip(-1,1); s=f32(opponent)-f32(self)','train_weight':'1/(96*n_game)','validation_used_in_fit':False}
result={s:{'distance':metrics(rr,predict),'constant':metrics(rr,lambda r:my),'cohorts':{str(p):{'distance':metrics([r for r in rr if r['opening_ply']==p],predict),'constant':metrics([r for r in rr if r['opening_ply']==p],lambda r:my)} for p in (8,12,16,20,24,28)}} for s,rr in [('train',train),('validation',val)]}
comparison={}
for name,p in [('WD0',pathlib.Path('research-data/ai-sigma/frame14-learning/runs/frame14-train96-r1')),('L2WD01',pathlib.Path('research-data/ai-sigma/frame14-l2-control/runs/frame14-l2-r1'))]:
 hist=[json.loads(x) for x in read(p/'history.jsonl').splitlines()];data=load(p/'dataset.json');cfg=load(p/'config.json');summary=load(p/'summary.json')
 assert data['counts']=={'train':4653,'validation':1248} and data['stage_manifest']['mask_sha256']==snap[str(A/'fixed-exposure-mask.json')]
 eq(data['constant'],my);assert summary['best_step']==0 and cfg['training']['target']=='rootmean'
 comparison[name]={'initial':hist[0],'LAST':hist[-1],'saved_only_no_forward_recertification':True}
sourcepaths=['tools/ai-sigma-nnue-qf1-prototype/qf1.cjs','tools/nnue-training/export_generated.cjs','tools/nnue-training/model.py','tools/nnue-training/frame14_data.py','tools/nnue-training/train.py','tools/ai-sigma-manygame-generation/worker.cjs','tools/ai-sigma-manygame-generation/schema.cjs','tools/ai-sigma-native-baseline/game.js','tools/ai-sigma-native-baseline/reference-core-native.js','tools/ai-sigma-native-baseline/private/src/lib.rs','tools/ai-sigma-frame14-teachers/export.cjs']
binding=load(P/'binding.json').get('readonly',{});source_bind={}
for p in sourcepaths:
 read(p)
 if p in binding:
  assert snap[p]==binding[p],('producer source binding differs',p)
  source_bind[p]={'hash':snap[p],'producer_bound':True}
 else:source_bind[p]={'hash':snap[p],'producer_bound':False,'scope':'current stopped source snapshot only'}
for p,h in snap.items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,('changed',p)
out={'status':'PASS_FINITE_VIEW_FIELDS_AND_DISTANCE_ARITHMETIC','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'wall_s':time.monotonic()-start,'peak_RSS_B':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'fit':fit,'metrics':result,'witnesses':witness,'trainval_games_winner_prefix':120,'z_rows_checked':5901,'readset_SHA':snap,'source_binding':source_bind,'archive_member_SHA':member_hashes,'QF1_saved_comparison':{k:{point:{split:v[point][split] for split in ('train','validation')} for point in ('initial','LAST')} for k,v in comparison.items()},'limits':['12 label-free-selected witnesses only for full648/QF1 field transform','Terminal winner check from saved120 final pawn prefixes, no full RuleA independent legality replay','No saved CP sums at witnesses; rootmean field source chain and raw/teacher/label binding only','No new NN/forward, no test reads; validation is reused diagnosis not independent test','Rootmean teacher is not true value; regression is a single train-only analytical baseline']}
(D/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ('status','UTC','pid','wall_s','peak_RSS_B','fit','metrics')}))
