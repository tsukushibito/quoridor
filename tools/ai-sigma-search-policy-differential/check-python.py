import json,struct,math,datetime,subprocess,os
from pathlib import Path
R=Path('/workspaces/quoridor/.worktree/ai-sigma');O=R/'.artifacts/ai-sigma/resume-20261002/SEARCH-POLICY';data=json.loads((O/'small-input.json').read_text());node=json.loads((O/'node-result.json').read_text())
def f(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def val(x):return struct.unpack('<f',struct.pack('<I',x))[0]
def tie(a,seed=1979):
 x=seed^a;x=((x^(x>>30))*0xbf58476d1ce4e5b9)&((1<<64)-1);x=((x^(x>>27))*0x94d049bb133111eb)&((1<<64)-1);return x^(x>>31)
def select(es,N,C=1.5,plus=True,first=False,unvisited=0):
 root=f(math.sqrt(f(f(N)+int(plus))));rows=[]
 for action,p,n,v,rank in es:
  prior=val(p);vs=val(v);q=f(vs/f(n)) if n else f(unvisited);score=f(q+f(f(f(f(C)*prior)*root)/f(n+1)));rows.append({'action':action,'score':score,'score_bits':bits(score)})
 best=rows[0]
 for row in rows[1:]:
  if row['score']>best['score'] or row['score']==best['score'] and not first and tie(row['action'])<tie(best['action']):best=row
 return {k:best[k] for k in ['action','score_bits']}
results=[]
for r in data['real_saved_roots']:
 assert sum(e[2] for e in r['edges'])==r['edge_sum'] and r['N_restored']==r['edge_sum']+1
 assert max(r['edges'],key=lambda e:(e[2],val(e[1]),-tie(e[0],r['seed'])))[0]==r['expected_finish']
 variants={'base':select(r['edges'],r['N_restored']),'C1':select(r['edges'],r['N_restored'],1),'sqrtN':select(r['edges'],r['N_restored'],1.5,False),'score_first':select(r['edges'],r['N_restored'],1.5,True,True)}
 nr=next(x for x in node['real_saved_roots'] if x['id']==r['id']);assert variants==nr['variations'];results.append({'id':r['id'],'variations':variants})
for case in node['backup_cases']:
 d=case['depth'];v=case['leaf_value'];expected=[(-1 if (d-i)%2 else 1)*v for i in range(d+1)];assert case['node_values']==expected;assert case['parent_edge_values']==expected[:-1];assert all(case['parent_edge_values'][i]==-case['node_values'][i+1] for i in range(d))
art=[]
for name,pq,q in [('negative-parent',-.4,.2),('positive-parent',.7,.8)]:
 es=[[3,bits(.8),9,bits(q*9),0],[5,bits(.2),0,bits(0),1]];p=val(bits(.8));fpu=pq-.2*math.sqrt(p);baseline=select(es,10,1,False,False,0);factor=select(es,10,1,False,False,fpu);actual=next(x for x in node['artificial'] if x['name']==name);assert actual['Q0_action']==baseline['action'] and actual['FPU_only_action']==factor['action'];assert abs(actual['FPU']-fpu)<1e-12;art.append({'name':name,'Q0':baseline,'FPU':factor,'known_parentQ':pq})
assert node['finish_gate']=={'n':6,'pass':6};assert next(x for x in node['artificial'] if x['name']=='parent-Q-not-edge-average')['parentQ']==.375
result={'issue':'quoridor-4lc.94','run':os.environ.get('SIGMA_POLICY_RUN','python-policy-unspecified'),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'Git':subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip(),'real_roots':results,'Action_scorebits_agree':24,'backup_cases_agree':len(node['backup_cases']),'known_parent_FPU_cases':art,'failures':[],'NN':0,'full765_replay':False}
(O/'python-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'Action_scorebits_agree':24,'backup_cases_agree':len(node['backup_cases']),'artificial_FPU':art,'failures':[]}))
