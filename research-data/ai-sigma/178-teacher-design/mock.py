import json,pathlib,time,datetime,os,hashlib,math,resource,copy
from fractions import Fraction as F
os.sched_setaffinity(0,{0});begin=time.monotonic();D=pathlib.Path(__file__).parent
def phi(a):
 if a<8:return [1,0,2,3,6,7,4,5][a]
 base=8 if a<72 else 72;p=a-base;return base+(7-p//8)*8+p%8
def canonical(action,own,other,side):
 if action>=145:k=72+action-145
 elif action>=81:k=8+action-81
 else:
  dest=(action%9,action//9); dx,dy=dest[0]-own[0],dest[1]-own[1];unit=((dx>0)-(dx<0),(dy>0)-(dy<0));directions=[(0,1),(0,-1),(-1,0),(1,0),(-1,1),(1,1),(-1,-1),(1,-1)];k=directions.index(unit);step=(own[0]+unit[0],own[1]+unit[1])
  if (unit[0]==0 or unit[1]==0) and step==other:step=(step[0]+unit[0],step[1]+unit[1])
  assert step==dest,'jump landing'
 return phi(k) if side==1 else k
def signature(state):return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()
mapping={a:canonical(a,(4,5),(4,4),1) for a in [31,81,145]};assert mapping=={31:0,81:64,145:128};assert all(phi(phi(a))==a for a in range(136))
counts={31:42,81:14,145:7};pi=[F(0)]*136
for a,n in counts.items():pi[mapping[a]]=F(n,63)
assert sum(pi)==1 and pi[0]==F(2,3) and pi[64]==F(2,9) and pi[128]==F(1,9)
state={'side':1,'key':'4,4|4,5|1||','history':[['4,4|4,5|1||',1]],'remaining':[10,10]};row={'state':state,'state_signature':signature(state),'mapping':mapping,'visits':counts,'pi':pi,'rootN':64,'edgeSum':63,'root_valueSum':-16.,'rootmean_stm':-.25,'rootmean_p1':.25,'rootNN_stm':.8,'rootNN_p1':-.8,'leafNN':None,'winner':1,'terminal':'GOAL','z_stm':-1,'z_p1':1,'NN_started':22,'NN_returned':22,'discarded':2,'terminal_noNN':44,'sampled_action':145,'sampling_temperature':1,'new_ply':0}
def validate(r):
 assert r['state_signature']==signature(r['state'])
 assert r['rootN']==64 and r['edgeSum']==63==sum(r['visits'].values())
 assert set(r['mapping'])==set(r['visits']) and len(set(r['mapping'].values()))==len(r['mapping'])
 expected=[F(0)]*136
 for a,n in r['visits'].items():assert type(n)==int and n>=0;expected[r['mapping'][a]]=F(n,63)
 assert r['pi']==expected and sum(r['pi'])==1
 sign=1 if r['state']['side']==0 else -1
 assert r['rootmean_stm']==r['root_valueSum']/r['rootN'] and r['rootmean_p1']==sign*r['rootmean_stm'] and r['rootNN_p1']==sign*r['rootNN_stm']
 z=0 if r['terminal']=='DRAW' else (1 if r['winner']==1 else -1) if r['terminal']=='GOAL' else None
 assert r['z_p1']==z and r['z_stm']==(sign*z if z is not None else None)
 assert r['NN_started']==r['NN_returned'] and r['rootN']==r['NN_returned']-r['discarded']+r['terminal_noNN']
 assert r['sampled_action'] in r['mapping']
validate(row);cases=[]
for name,change in [('illegal_mass',lambda r:r['pi'].__setitem__(1,F(1,100))),('rootN_pi_denominator',lambda r:r['pi'].__setitem__(0,F(42,64))),('wrong_P2_value',lambda r:r.update(z_stm=1)),('state_signature',lambda r:r['state'].update(side=0)),('bad_edge_count',lambda r:r['visits'].__setitem__(31,43))]:
 bad=copy.deepcopy(row);change(bad)
 try:validate(bad)
 except AssertionError:cases.append(name)
 else:raise AssertionError('accepted '+name)
truncated=copy.deepcopy(row);truncated.update(terminal='LIMIT',winner=None,z_p1=None,z_stm=None);validate(truncated);assert truncated['pi']==row['pi']
bad=copy.deepcopy(truncated);bad.update(z_p1=0,z_stm=0)
try:validate(bad)
except AssertionError:cases.append('truncation_is_not_draw')
else:raise AssertionError('accepted censored draw')
draw=copy.deepcopy(row);draw.update(terminal='DRAW',winner=None,z_p1=0,z_stm=0);validate(draw)
onehot=[F(int(i==mapping[row['sampled_action']])) for i in range(136)];assert onehot!=pi
terminal_root={'rootN':0,'edgeSum':0,'pi':None,'rootNN':None,'z_p1':1,'policy_loss_mask':False};assert terminal_root['pi'] is None
def split(game):return 'validation' if int(hashlib.sha256(game.encode()).hexdigest(),16)%5==0 else 'train'
assert len({split('game-1') for _ in range(4)})==1
folds={};conflict=False
for g,f in [('game-1','train'),('game-1','validation')]:
 if g in folds and folds[g]!=f:conflict=True
 folds[g]=f
assert conflict
out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'CPU':[0],'PID':os.getpid(),'elapsed_seconds':time.monotonic()-begin,'RSS_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rejected_cases':cases,'P2_mapping':mapping,'pi_nonzero':[[i,str(x)] for i,x in enumerate(pi) if x],'rootN':64,'edgeSum':63,'NN_started':22,'NN_returned':22,'discarded':2,'terminal_noNN':44,'z_unknown_separate_policy_valid':True,'sampling_action_not_pi':True,'game_split_repeated_lineage_detected':True,'terminal_root_no_policy':True,'permutation_involution_136':True,'new_NN':0,'new_game':0,'scope':'synthetic arithmetic/schema; actual RuleA legality/176 source execution/backend not certified'}
(D/'mock-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
