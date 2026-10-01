import json,math,statistics,struct,hashlib,datetime,collections,subprocess
from pathlib import Path
R=Path('/workspaces/quoridor/.worktree/ai-sigma');O=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SAVED-NN46-INDEPENDENT';B=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-NN-SCHEMA-COST';C='a62819d4ef6b9c63587e7c20dbe6344c5ded5045'
inputs={};fail=[]
def load(p):
 p=Path(p);data=p.read_bytes();inputs[str(p.relative_to(R))]=hashlib.sha256(data).hexdigest();return json.loads(data)
def require(ok,label):
 if not ok:fail.append(label)
def close(a,b):return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-4+1e-4*abs(b)
def bits(a):return list(struct.unpack('<'+'I'*len(a),struct.pack('<'+'f'*len(a),*a)))
def summarize(v):return {'n':len(v),'min':min(v),'median':statistics.median(v),'mean':statistics.mean(v),'max':max(v),'stdev':statistics.stdev(v) if len(v)>1 else 0,'all_ms':v}
def same(a,b,path):
 if isinstance(b,dict):
  for k,v in b.items():require(k in a,path+'.'+k+'.missing');same(a[k],v,path+'.'+k) if k in a else None
 elif isinstance(b,list):
  require(len(a)==len(b),path+'.length')
  for i,(u,v) in enumerate(zip(a,b)):same(u,v,path+f'[{i}]')
 elif isinstance(b,(float,int)) and not isinstance(b,bool):require(abs(a-b)<=1e-8,path+'.algebra')
 else:require(a==b,path+'.value')
fpath=R/'.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json';rpath=R/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'
fixtures={f['id']:f for f in load(fpath)['fixtures']};refs={f['id']:f for f in load(rpath)}
require(inputs[str(fpath.relative_to(R))]=='206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb','fixture_fixed_hash');require(inputs[str(rpath.relative_to(R))]=='060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a','ORT_reference_fixed_hash')
reportpath=R/'docs/reports/ai-sigma-experiment-nn-schema-cost.md';inputs[str(reportpath.relative_to(R))]=hashlib.sha256(reportpath.read_bytes()).hexdigest()
pr=load(B/'preregister-v2-r1.json');require(inputs[str((B/'preregister-v2-r1.json').relative_to(R))]=='631426f7f9b20e6d737f7a38c791e333aae167bf1607377d667e5b6849799542','preregister_hash')
stop=load(B/'runtime-source-stopped-before-report.json');require(inputs[str((B/'runtime-source-stopped-before-report.json').relative_to(R))]=='eb713d37695dde380f98ff614e7e713184001a682509f1eec6d4e63c9fcaa51d','stop_hash')
claim=load(B/'cost-and-numeric-summary.json');load(B/'handoff-summary.json');load(R/'docs/reports/ai-sigma-experiment-nn-schema-cost.md') if False else None
# Verify committed source binding, without importing any model/engine code.
sourcechecks=[]
for x in pr['source']:
 path=Path(x['path']).relative_to(R);v=subprocess.run(['git','show',C+':'+str(path)],check=True,stdout=subprocess.PIPE).stdout
 h=hashlib.sha256(v).hexdigest();require(h==x['sha256'],'Git_source:'+str(path));sourcechecks.append({'path':str(path),'sha256':h,'matches':h==x['sha256']})
# Independently derive vertical Action permutation. Direction order is fixed upstream.
perm=[1,0,2,3,6,7,4,5]+[8+(7-(i//8))*8+i%8 for i in range(64)]+[72+(7-i//8)*8+i%8 for i in range(64)]
def from_board(f):
 b=f['board'];hw=b['h_segments'];vw=b['v_segments']
 def distances(goal):
  d=[81]*81;q=collections.deque()
  for x in range(9):d[goal*9+x]=0;q.append((x,goal))
  while q:
   x,y=q.popleft()
   for dx,dy in [(0,1),(0,-1),(-1,0),(1,0)]:
    xx,yy=x+dx,y+dy
    if not(0<=xx<9 and 0<=yy<9):continue
    blocked=hw[y*9+x] if dy==1 else hw[(y-1)*9+x] if dy==-1 else vw[y*9+x] if dx==1 else vw[y*9+x-1]
    if not blocked and d[yy*9+xx]==81:d[yy*9+xx]=d[y*9+x]+1;q.append((xx,yy))
  return d
 ds=[distances(8),distances(0)];side=b['turn'];opp=1-side;out=[0.0]*648
 for channel,who in [(0,side),(1,opp)]:
  x,y=b['pawns'][who];out[channel*81+(8-y if side else y)*9+x]=1
 for y in range(9):
  for x in range(9):
   i=y*9+x;out[162+i]=hw[(7-y)*9+x] if side and y<8 else 0 if side else hw[i];out[243+i]=vw[(8-y)*9+x] if side else vw[i]
   out[324+i]=b['walls_remaining'][side]/10;out[405+i]=b['walls_remaining'][opp]/10
   j=(8-y)*9+x if side else i
   for channel,who in [(6,side),(7,opp)]:out[channel*81+i]=ds[who][j]/80 if ds[who][j]<81 else 1
 return bits(out)
feature_board_checks=0
for f in fixtures.values():
 require(f['P2_permutation136']==perm,f['id']+'.P2perm')
 require(from_board(f)==bits(f['raw_features_float32']),f['id']+'.independent_board_feature_bits');feature_board_checks+=648
 b=f['board'];winner=1 if b['pawns'][0][1]==8 else 2 if b['pawns'][1][1]==0 else 0;ending=winner!=0 or b['total_ply']>=200 or not f['legal_actions'];tv=(1 if winner==b['turn']+1 else -1) if winner else 0 if ending else None;require(f['terminal']['winner']==winner and f['terminal']['side_to_move_value']==tv,f['id']+'.goalpriority_terminal')
 fb=bits(f['raw_features_float32']);sha=hashlib.sha256(struct.pack('<648I',*fb)).hexdigest();require(sha==refs[f['id']]['input_float32_sha256'],f['id']+'.reference_feature_sha')
 for a in f['legal_actions']:
  if a['action']['type']=='wall':
   x=a['action']['x'];y=a['action']['y'];h=a['action']['orientation']=='h';require(a['sigma136']==(8 if h else 72)+y*8+x,f['id']+'.wall136');require(a['rust209']==(81 if h else 145)+y*8+x,f['id']+'.wall209')
  else:
   x,y=a['pawn_landing'];require(a['rust209']==y*9+x,f['id']+'.pawn209');dx,dy=a['action']['direction'];cx,cy=f['board']['pawns'][f['board']['turn']];ox,oy=f['board']['pawns'][1-f['board']['turn']];scale=2 if (dx==0 or dy==0) and (cx+dx,cy+dy)==(ox,oy) else 1;require([cx+scale*dx,cy+scale*dy]==[x,y],f['id']+'.independent_jump_landing');require(a['sigma136']==[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)].index((dx,dy)),f['id']+'.direction136')
 require(f['canonical_legal_indices']==[(perm[a['sigma136']] if f['board']['turn'] else a['sigma136']) for a in f['legal_actions']],f['id']+'.canonical')
rows=[];hp=hashlib.sha256()
with (B/'runs/v2-r1/calls.jsonl').open('rb') as stream:
 for line in stream:hp.update(line);rows.append(json.loads(line))
inputs[str((B/'runs/v2-r1/calls.jsonl').relative_to(R))]=hp.hexdigest()
# Schema inventory is recorded before full arithmetic gates, with no raw duplication.
inventory={'n':len(rows),'by_backend':dict(collections.Counter(r['backend'] for r in rows)),'by_phase':dict(collections.Counter(r['phase'] for r in rows)),'schemas':{side:sorted(set().union(*(r.keys() for r in rows if r['backend']==side))) for side in ['A','B']},'first_last':[(r['id'],r['backend'],r['phase']) for r in [rows[0],rows[-1]]],'terminals':[(r['id'],r['backend'],len(r['raw_legal']),len(r['effective_legal'])) for r in rows if fixtures[r['id']]['terminal']['side_to_move_value'] is not None]}
(O/'schema-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
require(len(rows)==92,'92rows');require(inventory['by_backend']=={'A':46,'B':46},'46each')
metrics={s:{kind:collections.defaultdict(list) for kind in ['warm','steady']} for s in ['A','B']};percase={};maxdiff=0;maxprior=0;totalprior=0;effective_terminal=0;terminal_field_null=0;gaterows=[];latency=[];checks=0
for index,r in enumerate(rows):
 f=fixtures[r['id']];ref=refs[r['id']];label=f"row{index+1}:{r['backend']}:{r['id']}";A=r['backend']=='A';logits=r['policy_logits'] if A else r['logits'];v=r['value'];end=f['terminal']['side_to_move_value'] is not None
 require(len(logits)==136 and all(math.isfinite(x) for x in logits),label+'.logit_shapefinite');require(math.isfinite(v) and -1<=v<=1,label+'.strictvalue');require(r['features_bits']==bits(f['raw_features_float32']),label+'.648bits')
 require(('classification' in r and r['classification']==f['classification'] and r.get('search')==[] and 'logits' not in r) if A else ('search' not in r and 'policy_logits' not in r and r['turn']==f['board']['turn'] and r['terminal']==f['terminal']['side_to_move_value']),label+'.schema')
 for u,w in zip(logits+[v],ref['policy_logits']+[ref['value']]):require(close(u,w),label+'.NNgate');maxdiff=max(maxdiff,abs(u-w));checks+=1
 mapping={a['rust209']:(perm[a['sigma136']] if f['board']['turn'] else a['sigma136']) for a in f['legal_actions']};ids=sorted(mapping);require(r['raw_legal']==ids,label+'.own_raw_order');require(r['effective_legal']==([] if end else ids),label+'.effective_legal');require(len(r['raw_prior'])==len(ids),label+'.rawprior_shape');totalprior+=len(ids)
 def soft(xs):
  if not xs:return []
  w=[math.exp(x-max(xs)) for x in xs];den=math.fsum(w);return [x/den for x in w]
 selfprior=soft([logits[mapping[i]] for i in ids]);target=soft([ref['policy_logits'][mapping[i]] for i in ids])
 for u,w,z in zip(r['raw_prior'],selfprior,target):require(0<=u<=1 and close(u,w) and close(u,z),label+'.priorgate');maxprior=max(maxprior,abs(u-z))
 require(not ids or close(math.fsum(r['raw_prior']),1),label+'.sumprior')
 if end:effective_terminal+=1;require(ref['canonical_legal_priors'] is None,label+'.reference_effective_null')
 else:
  for action,prior in zip(f['legal_actions'],ref['canonical_legal_priors']):require(prior['canonical136']==mapping[action['rust209']] and close(prior['prior'],target[ids.index(action['rust209'])]),label+'.reference_prior')
 encoded=r['formatted_json'].encode('utf8');fmt=json.loads(r['formatted_json']);require(len(encoded)==r['formatted_bytes'],label+'.UTF8');require(fmt['features_bits']==r['features_bits'] and fmt['logits']==logits and fmt['value']==v and fmt['raw_legal']==ids and fmt['raw_prior']==r['raw_prior'] and fmt['effective_legal']==r['effective_legal'],label+'.formatted_identity')
 require(fmt['backend']==r['backend'] and fmt['id']==r['id'],label+'.formatted_id')
 sp=r['spans'];whole=sp['whole_end_ms']-sp['whole_start_ms'];encodedwhole=sp['format_encoding_end_ms']-sp['whole_start_ms'];require(abs(whole-r['whole_call_ms'])<=1e-9,label+'.whole_call_ms');require(sp['whole_end_ms']>=sp['format_encoding_end_ms'],label+'.whole_end_afterencoding')
 layer={'whole_wrapper':whole,'Node_transport_whole':r['Node_end']-r['Node_start'],'input_clone':sp['input_clone_end_ms']-sp['whole_start_ms'],'input_validation':sp['input_validation_end_ms']-sp['input_clone_end_ms'],'output_validation':sp['validation_end_ms']-sp['validation_start_ms'],'format_UTF8':sp['format_encoding_end_ms']-sp['format_start_ms']}
 if A:layer['opaque_ABI']=sp['opaque_ABI_end_ms']-sp['opaque_ABI_start_ms'];require(sp['A_kernel_span'] is None,label+'.opaque')
 else:
  q=sp['B_infer'];layer.update(feature_only=sp['feature_only_end_ms']-sp['feature_only_start_ms'],feature_bits_copy=q['tensor_start_ms']-q['whole_start_ms'],tensor=q['tensor_end_ms']-q['tensor_start_ms'],run_API_await=q['run_end_ms']-q['run_start_ms'],output_extraction=q['output_check_end_ms']-q['run_end_ms'],raw_policy=sp['policy_end_ms']-sp['policy_start_ms'])
 require(all(math.isfinite(x) and x>=0 for x in layer.values()),label+'.durationfinite');require(layer['Node_transport_whole']>=0,label+'.Nodeinterval')
 if r['phase']=='latency':
  latency.append(r);kind='warm' if r['warm'] else 'steady';require(r['sample']==-1 if r['warm'] else 0<=r['sample']<=4,label+'.warm_sample')
  for k,z in layer.items():metrics[r['backend']][kind][k].append(z)
  percase.setdefault(r['id'],{}).setdefault(r['backend'],{'warm':[],'steady':[]})[kind].append(layer)
 else:gaterows.append(r)
for records,order,phase in [(gaterows,pr['gate_order'],'numeric'),(latency,pr['latency_order'],'latency')]:
 require(len(records)==len(order),phase+'.count')
 for r,w in zip(records,order):
  for k,v in w.items():require(r[k]==v,phase+'.preregister_order.'+k)
recomputed={s:{k:{name:summarize(values) for name,values in layers.items()} for k,layers in kinds.items()} for s,kinds in metrics.items()}
same(recomputed,claim['all_warm_and_samples'],'cost_claim')
for name,sides in percase.items():
 for side,v in sides.items():same(summarize([x['whole_wrapper'] for x in v['steady']]),claim['per_fixture'][name][side]['steady'],'perfixture.'+name+'.'+side);same(v['warm'],claim['per_fixture'][name][side]['warm'],'perfixturewarm')
clock={}
for endpoint in ['start','end']:
 z=load(B/f'runs/v2-r1/clock-{endpoint}.json');clock[endpoint]={}
 for side in ['page','worker']:
  obj=z[side];print('clock_schema',endpoint,side,list(obj))
  samples=obj['samples'];lo=max(x['remote']-x['end']-.1 for x in samples);hi=min(x['remote']-x['start']+.1 for x in samples);require(len(samples)==12 and lo<=hi,'clock_'+endpoint+'_'+side);require(abs(lo-obj['lo'])<1e-8 and abs(hi-obj['hi'])<1e-8 and abs(obj['error_ms']-((hi-lo)/2+.1))<1e-8 and abs(obj['offset_ms']-(hi+lo)/2)<1e-8,'clock_fit_'+endpoint+'_'+side);clock[endpoint][side]={'lo':lo,'hi':hi,'error':(hi-lo)/2+.1,'n':len(samples)}
for side in ['page','worker']:
 st=clock['start'][side];en=clock['end'][side];calc={'start_interval':[st['lo'],st['hi']],'end_interval':[en['lo'],en['hi']],'drift_interval':[en['lo']-st['hi'],en['hi']-st['lo']],'overlap':max(st['lo'],en['lo'])<=min(st['hi'],en['hi']),'samples_each':12};same(calc,claim['clock'][side],'clockclaim.'+side)
require(rows[-1]['count']=={'A_attempt':46,'A_complete':46,'B_attempt':46,'B_complete':46,'raw_feature_calls':74,'raw_policy_calls':46,'search_calls':0},'final_count')
format_intervals={side:{kind:summarize([r['spans']['format_encoding_end_ms']-r['spans']['whole_start_ms'] for r in latency if r['backend']==side and r['warm']==(kind=='warm')]) for kind in ['warm','steady']} for side in ['A','B']}
result={'run':'verify83-old46-r3','checker_git':subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip(),'issue':'quoridor-4lc.84','contract':3,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'input_git':C,'inventory':inventory,'numeric':{'numeric56':len(gaterows),'latency36':len(latency),'A46_B46':inventory['by_backend'],'features_bits':len(rows)*648,'independent_board_feature_bits':feature_board_checks,'NN_elements':checks,'prior_elements':totalprior,'max_NN_absdiff':maxdiff,'max_prior_absdiff':maxprior,'raw_terminal_calls':effective_terminal,'effective_prior_null':'fixed reference null / effective legal [] verified; raw formatted wrapper omits explicit effective_prior field','new_NN':0},'cost':recomputed,'whole_start_to_format_encoding_end':format_intervals,'whole_minus_encoding_max_ms':max(r['spans']['whole_end_ms']-r['spans']['format_encoding_end_ms'] for r in rows),'per_fixture':{name:{side:{'warm_n':len(v['warm']),'steady':summarize([x['whole_wrapper'] for x in v['steady']])} for side,v in sides.items()} for name,sides in percase.items()},'clock':clock,'failures':fail,'source_git_checks':sourcechecks,'cost_claim_matches':not fail,'inputs_before':inputs,'limits':['saved arithmetic only; no independent NN execution','opaque ABI and full B wrapper are different decompositions; no pure NN ratio','B context processed twice; run await not kernel instruction interval','finite one-window sample; no tail/strength/NI inference','parent operational text excluded from numeric mismatch'],'actual_go':False}
# Old80 is a distinct, incomplete denominator; reuse the same bits/softmax/mapping gates.
oldbase=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-ISOLATED-NN-COST';old=[];oh=hashlib.sha256()
with (oldbase/'calls.jsonl').open('rb') as stream:
 for line in stream:oh.update(line);old.append(json.loads(line))
inputs[str((oldbase/'calls.jsonl').relative_to(R))]=oh.hexdigest();oldfail=[];oldmax=0;oldprior=0
for n,r in enumerate(old):
 f=fixtures[r['id']];ref=refs[r['id']];A=r['backend']=='A';lg=r['policy_logits'] if A else r['logits'];v=r['value'];ids=sorted(a['rust209'] for a in f['legal_actions']);mapping={a['rust209']:(perm[a['sigma136']] if f['board']['turn'] else a['sigma136']) for a in f['legal_actions']}
 if len(lg)!=136 or not all(math.isfinite(x) for x in lg) or not(-1<=v<=1) or not math.isfinite(v):oldfail.append([n,'shape/finite/value'])
 if r['features_bits']!=from_board(f) or r['raw_legal']!=ids or r['effective_legal']!=([] if f['terminal']['side_to_move_value'] is not None else ids):oldfail.append([n,'features/legal'])
 if (A and (r.get('classification')!=f['classification'] or r.get('search')!=[])) or (not A and ('search' in r or r.get('turn')!=f['board']['turn'] or r.get('terminal')!=f['terminal']['side_to_move_value'])):oldfail.append([n,'schema'])
 for x,y in zip(lg+[v],ref['policy_logits']+[ref['value']]):
  if not close(x,y):oldfail.append([n,'NN'])
  oldmax=max(oldmax,abs(x-y))
 expected=soft([ref['policy_logits'][mapping[i]] for i in ids]);own=soft([lg[mapping[i]] for i in ids])
 if len(r['raw_prior'])!=len(ids):oldfail.append([n,'prior_shape'])
 for x,y,z in zip(r['raw_prior'],expected,own):
  if not(0<=x<=1 and close(x,y) and close(x,z)):oldfail.append([n,'prior'])
  oldprior=max(oldprior,abs(x-y))
 if r['ordinal']!=n+1:oldfail.append([n,'ordinal'])
oldfailure=load(oldbase/'failures.jsonl');result['old80']={'saved_n':len(old),'saved_by_backend':dict(collections.Counter(r['backend'] for r in old)),'failures':oldfail,'max_NN_absdiff':oldmax,'max_prior_absdiff':oldprior,'features_bits':len(old)*648,'NN_elements':len(old)*137,'last_saved':old[-1]['id'],'raw_attempt_counts_from_failure_record':oldfailure['producer']['count'],'unsaved_output_47':'not reconstructed','unexecuted_numeric':9,'latency36':'not started; no cost inference','old81_insufficient_checker':'not retroactively changed','not_pooled_with83':True}
require(len(old)==46 and result['old80']['saved_by_backend']=={'A':23,'B':23},'old80savedcount');require(not oldfail,'old80numeric')
# No faulty sentinel is accepted by the shared numerical predicate.
require(not close(float('nan'),0) and not close(float('inf'),0) and close(1e-4,0) and not close(1.00001e-4,0),'predicate_boundary')
result['failures']=fail;result['cost_claim_matches']=not fail
(O/'independent83.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'n':len(rows),'failures':fail,'maxdiff':maxdiff,'maxprior':maxprior,'medians':{s:recomputed[s]['steady']['whole_wrapper']['median'] for s in ['A','B']}}));raise SystemExit(1 if fail else 0)
