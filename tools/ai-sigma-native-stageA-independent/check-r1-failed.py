"""168 saved arithmetic. Reuses critic153 BFS/ledger; no inference imports or owner checker."""
import collections,datetime,hashlib,json,math,pathlib,struct,os,resource
os.sched_setaffinity(0,{0})
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/168-native-stageA-independent'
refs=[]
def read(p):
 p=R/p if not pathlib.Path(p).is_absolute() else pathlib.Path(p);b=p.read_bytes();refs.append({'path':str(p.relative_to(R)),'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()});return json.loads(b)
raw=read('.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/runs/native165-mechanism-r1/result.json');assert refs[-1]['SHA256']=='dee3d3b52839b3c8ba50c082abba835be6f0784c61617a37ccfa550811113286'
fixtures={f['id']:f for f in read('research-data/ai-sigma/165-native-baseline/stageA-inputs.json')['fixtures']}
metrics=collections.Counter();maxdiff=collections.defaultdict(float);firstnumeric=None;location=None
compact=[]
def exact(a,b,label):
 assert a==b,(location,label,a,b);metrics[label]+=1
def near(a,b,label):
 global firstnumeric
 assert math.isfinite(a) and math.isfinite(b)
 delta=abs(a-b);assert delta<=1e-12+1e-12*abs(b),(location,label,a,b)
 maxdiff[label]=max(maxdiff[label],delta)
 if delta and firstnumeric is None:firstnumeric={'location':location,'field':label,'left':a,'right':b,'abs':delta}
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def unpackkey(s):
 p,q,t,h,v=s.split('|');return [list(map(int,p.split(','))),list(map(int,q.split(',')))],int(t),[set(x.split(';'))-{''} for x in [h,v]]
def key(p,t,w):return '|'.join([','.join(map(str,p[0])),','.join(map(str,p[1])),str(t),';'.join(sorted(w[0])),';'.join(sorted(w[1]))])
dirs=[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)]
def policyindex(a,p,t):
 if a>=81:return a-81+8 if a<145 else a-145+72
 dx,dy=a%9-p[t][0],a//9-p[t][1]
 if dx==0:dy=(dy>0)-(dy<0)
 elif dy==0:dx=(dx>0)-(dx<0)
 return dirs.index((dx,dy))
def canonical(i,t):
 if not t:return i
 if i<8:return [1,0,2,3,6,7,4,5][i]
 off=8 if i<72 else 72;j=i-off;return off+(7-j//8)*8+j%8
def featurebits(p,t,w,remain):
 # Independent adjacency graph and reverse BFS, not a translation of owner checker.
 blocked=set();hs=[0]*81;vs=[0]*81
 for s in w[0]:
  x,y=map(int,s.split(','))
  for cx in (x,x+1):
   hs[9*y+cx]=1;blocked.add(frozenset((9*y+cx,9*(y+1)+cx)))
 for s in w[1]:
  x,y=map(int,s.split(','))
  for cy in (y,y+1):
   vs[9*cy+x]=1;blocked.add(frozenset((9*cy+x,9*cy+x+1)))
 maps=[]
 for goal in (8,0):
  dist=[81]*81;q=collections.deque(range(9*goal,9*goal+9))
  for c in q:dist[c]=0
  while q:
   c=q.popleft();x,y=c%9,c//9
   for dx,dy in dirs[:4]:
    xx,yy=x+dx,y+dy
    if 0<=xx<9 and 0<=yy<9:
     n=yy*9+xx
     if dist[n]==81 and frozenset((c,n)) not in blocked:dist[n]=dist[c]+1;q.append(n)
  maps.append(dist)
 out=[0.0]*648
 for c,player in enumerate((t,1-t)):
  x,y=p[player];out[c*81+(8-y if t else y)*9+x]=1
 for y in range(9):
  for x in range(9):
   dst=y*9+x;src=(8-y if t else y)*9+x
   out[162+dst]=hs[(7-y if t else y)*9+x] if y<8 else 0
   out[243+dst]=vs[src]
   for c,player in enumerate((t,1-t)):
    out[(4+c)*81+dst]=remain[player]/10
    dd=maps[player][src];out[(6+c)*81+dst]=dd/80 if dd<81 else 1
 return list(map(bits,out))
def nextkey(p,t,w,a):
 p=[z[:] for z in p];w=[set(z) for z in w]
 if a<81:p[t]=[a%9,a//9]
 else:
  o=0 if a<145 else 1;n=a-(81 if o==0 else 145);w[o].add(f'{n%8},{n//8}')
 return p,1-t,w
def checkrow(row):
 f=fixtures[row['fixture_id']];exact(row['primary'],None,'primary');exact(row['K'],32,'K');exact(len(row['CPs']),32,'CPs');exact(len(row['numeric']),32,'NN');exact(len(row['trace']['backups']),32,'backups')
 # Reconstruct the allocation graph from NN legal order, and its ledger from leaf values.
 nodes={():{'id':0,'N':0,'sum':0.,'prior':1.,'children':[]}};nextid=1;selectcursor=0
 global location
 for k,(n,b,cp) in enumerate(zip(row['numeric'],row['trace']['backups'],row['CPs']),1):
  location={'fixture':f['id'],'engine':row['engine'],'K':k}
  exact(n['NN_bits'],[bits(v) for v in n['policy_logits']+[n['value']]],'NN137_bits')
  path=tuple(n['path']);exact(b['path'],list(path),'backup_path');exact(b['K'],k,'backupK')
  # Request state/history reconstructed from the root and the actual path.
  p,t,w=unpackkey(f['history_count_key']);hist=dict(f['history_counts']);remain=[10-sum(a['type']=='wall' for a in f['legal_prefix'][player::2]) for player in (0,1)]
  for a in path:
   if a>=81:remain[t]-=1
   p,t,w=nextkey(p,t,w,a);s=key(p,t,w);hist[s]=hist.get(s,0)+1
  exact(n['key'],key(p,t,w),'requestkey');exact(n['turn'],t,'side');exact(n['ply'],f['board']['total_ply']+len(path),'ply');exact(sorted(n['history']),[list(x) for x in sorted(hist.items())],'history')
  exact(n['features_bits'],featurebits(p,t,w,remain),'independent_features648')
  exact(len(n['policy_logits']),136,'logitsshape')
  for v in n['policy_logits']+[n['value']]:
   assert math.isfinite(v) and struct.unpack('<f',struct.pack('<f',v))[0]==v;metrics['f32_exact_extension']+=1
  assert -1<=n['value']<=1
  # Traverse each saved selection against all available sibling scores, strict first argmax.
  for depth,a in enumerate(path):
   s=row['trace']['selects'][selectcursor];selectcursor+=1;parent=nodes[path[:depth]];children=parent['children'];visited=0.
   for child in children:
    if nodes[child]['N']:visited+=nodes[child]['prior']
   pq=parent['sum']/parent['N'];scores=[]
   for child in children:
    z=nodes[child];q=-z['sum']/z['N'] if z['N'] else pq-.2*math.sqrt(visited);scores.append(q+z['prior']*math.sqrt(parent['N'])/(1+z['N']))
   chosen=children[max(range(len(children)),key=lambda i:scores[i])];exact(chosen,path[:depth+1],'strict_argmax_path')
   z=nodes[chosen]
   for field,value in [('K_before',k-1),('path_before',list(path[:depth])),('node_index',parent['id']),('nodeN',parent['N']),('nodeSum',parent['sum']),('childN',z['N']),('childSum',z['sum']),('Action',a)]:exact(s[field],value,field)
   for field,value in [('parentQ',pq),('childQ',z['sum']/z['N'] if z['N'] else 0),('score',max(scores)),('prior',z['prior']),('visited_base_prior_sum',visited)]:near(s[field],value,'computed_'+field)
  leaf=nodes[path];exact(n['node_index'],leaf['id'],'NNnodeindex');exact(b['leaf_index'],leaf['id'],'leafindex');exact(b['terminal'],None,'terminal_unobserved')
  indices=[policyindex(a,p,t) for a in n['legal']];order=[i if a<81 else 8+2*(a-81) if a<145 else 9+2*(a-145) for a,i in zip(n['legal'],indices)];exact(order,sorted(order),'original_order')
  vals=[n['policy_logits'][canonical(i,t)] for i in indices];mx=max(vals);ex=[math.exp(v-mx) for v in vals];den=0.
  for e in ex:den+=e
  for a,e in zip(n['legal'],ex):
   pp=path+(a,);assert pp not in nodes;nodes[pp]={'id':nextid,'N':0,'sum':0.,'prior':e/den,'children':[]};nextid+=1;leaf['children'].append(pp)
  exact(b['value_leaf_side'],n['value'],'leaf_value_from_NN');exact(len(b['updates']),len(path)+1,'ancestor_count')
  value=n['value']
  for j,u in enumerate(b['updates']):
   z=nodes[path[:len(path)-j]]
   for field,v in [('index',z['id']),('preN',z['N']),('preSum',z['sum']),('value',value)]:exact(u[field],v,'backup_'+field)
   z['N']+=1;z['sum']+=value;value=-value
  root=nodes[()];edges=cp['root_edges'];exact(len(edges),len(root['children']),'root_legal_count')
  for e,child in zip(edges,root['children']):
   z=nodes[child];exact(e[0],child[-1],'CP_legal_Action');exact(e[2],z['N'],'CP_childN');exact(e[3],z['sum'],'CP_childSum');near(e[1],z['prior'],'computed_prior')
  compact.append({'fixture':f['id'],'engine':row['engine'],'K':k,'generation':cp['generation'],'action':cp['action'],'rootN':cp['root_visits'],'edgeN':sum(e[2] for e in edges),'rootSum':cp['root_valueSum'],'mean':cp['root_mean'],'NN':cp['nn_calls'],'path':list(path),'side':n['turn']})
  chosen=max(range(len(edges)),key=lambda i:edges[i][2]);exact(cp['action'],edges[chosen][0],'finish_first_visits');exact(cp['root_visits'],k,'CP_rootN');exact(sum(e[2] for e in edges),k-1,'CP_edgeN');exact(cp['root_valueSum'],root['sum'],'CP_rootsum');exact(cp['root_mean'],root['sum']/k,'CP_true_mean');exact(cp['nn_calls'],k,'CP_NNcount')
  exact(cp['simulations'],k,'public_count_mapping')
 exact(selectcursor,len(row['trace']['selects']),'all_selects_checked');exact(row['completed'],32,'completed');exact(row['terminal_noNN'],0,'terminal_noNN');exact(row['zero'],{'handles':0,'activeNN':0,'active':False},'search_zero')
 return {'fixture':f['id'],'engine':row['engine'],'CPs':32,'NN':32,'selects':selectcursor,'Action':row['cp']['action'],'depth':max(len(n['path']) for n in row['numeric'])}

exact(len(raw['rows']),10,'rows');exact(raw['errors'],[],'errors');exact(raw['primary'],None,'primary');exact(raw['hand_NN'],320,'handNN');exact(raw['startup_NN'],2,'startup_separate')
rows=[checkrow(r) for r in raw['rows']]
firstpaired=None;maxpaired=collections.defaultdict(float)
for fid in fixtures:
 a,b=[next(r for r in raw['rows'] if r['fixture_id']==fid and r['engine']==e) for e in ['candidate','reference']]
 exact(a['root_state'],b['root_state'],'paired_rootstate')
 root=a['root_state'];f=fixtures[fid];exact(root['key'],f['history_count_key'],'fixed_rootkey');exact(root['history'],sorted(f['history_counts']),'fixed_roothistory');exact(root['legal'],[x['rust209'] for x in f['legal_actions']],'fixed_rootlegal');exact(root['features_bits'],[bits(x) for x in f['raw_features_float32']],'fixed_rootfeatures')
 for k,(n,m) in enumerate(zip(a['numeric'],b['numeric']),1):
  location={'fixture':fid,'K':k,'comparison':'candidate/reference'}
  for field in ['key','ply','turn','features_bits','legal','path','policy_logits','value','node_index','NN_bits']:exact(n[field],m[field],'paired_'+field)
  exact(sorted(n['history']),sorted(m['history']),'paired_history')
 exact(a['trace']['backups'],b['trace']['backups'],'paired_backups')
 for k,(n,m) in enumerate(zip(a['CPs'],b['CPs']),1):
  location={'fixture':fid,'K':k,'comparison':'CP'}
  for field in ['action','root_visits','root_valueSum','root_mean','simulations','nn_calls']:exact(n[field],m[field],'paired_CP_'+field)
  for edge,(ea,eb) in enumerate(zip(n['root_edges'],m['root_edges'])):
   for i in [0,2,3]:exact(ea[i],eb[i],'paired_edge_discrete_ledger')
   delta=abs(ea[1]-eb[1]);maxpaired['prior']=max(maxpaired['prior'],delta);near(ea[1],eb[1],'paired_prior')
   if delta and firstpaired is None:firstpaired={'fixture':fid,'K':k,'edge':edge,'Action':ea[0],'field':'prior','left':ea[1],'right':eb[1],'abs':delta}
 for k,(n,m) in enumerate(zip(a['trace']['selects'],b['trace']['selects'])):
  location={'fixture':fid,'selection_index':k};exact(set(n),set(m),'paired_select_schema')
  for field in n:
   if field in ['score','prior','visited_base_prior_sum']:
    near(n[field],m[field],'paired_select_'+field);maxpaired[field]=max(maxpaired[field],abs(n[field]-m[field]))
   else:exact(n[field],m[field],'paired_select_'+field)
 # The final public compact CP is the final completed CP, independently of clocks.
 for row in (a,b):exact(row['cp'],row['CPs'][-1],'final_CP')
for eng in ['candidate','reference']:
 i=raw['init'][eng];info=i['info'];exact(info['version'],'1.30.0','ORT_version');exact(info['providers'],['CPUExecutionProvider'],'CPU_provider');exact(info['intra'],1,'intra');exact(info['inter'],1,'inter');exact(info['sequential'],True,'sequential');exact(i['startup']['count'],1,'startup_count');exact(raw['closed'][eng]['receipt']['NN_total'],160,'engine_NN');exact(raw['closed'][eng]['receipt']['startup_separate'],1,'close_startup')
exact(raw['init']['candidate']['startup']['root_NN_bits'],raw['init']['reference']['startup']['root_NN_bits'],'paired_startup137')
out={'issue':'quoridor-4lc.168','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved_stageA_finite_support':True,'rows':rows,'CP_count':len(compact),'NN_count':sum(r['NN'] for r in rows),'startup_NN':2,'metrics':dict(metrics),'computed_max_numeric_abs':dict(maxdiff),'paired_max_numeric_abs':dict(maxpaired),'first_computed_numeric_difference':firstnumeric,'first_paired_numeric_difference':firstpaired,'first_discrete_difference':None,'first_ledger_difference':None,'references':refs,'new_NN':0,'native_binary_replay':0,'reused_critic153_arithmetic':True,'independence_limits':['saved outputs not rerun','RuleA legal lists partly shared; root bound to fixed fixtures','visited NN paths only; no unvisited all-deep/terminal proof','Python exp recomputation differs in last f64 bits; discrete comparison exact','sameK is not samewall/kernelCPU/NI'], 'RAM_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
assert out['RAM_peak_bytes']<939524096
(D/'analysis.json').write_text(json.dumps(out,indent=2)+'\n');(D/'compact-320CP.json').write_text(json.dumps(compact,separators=(',',':'))+'\n')
print(json.dumps({k:out[k] for k in ['saved_stageA_finite_support','CP_count','NN_count','startup_NN','first_paired_numeric_difference','paired_max_numeric_abs','RAM_peak_bytes']}))
