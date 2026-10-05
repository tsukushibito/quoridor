"""Discrete mechanism and arithmetic differences are independent; never round a path."""
import sys,json,math,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/165-native-baseline';run=sys.argv[1];p=R/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/runs'/run/'result.json';raw=json.loads(p.read_text());first_discrete=None;first_numeric=None;first_ledger=None;pairs=[]
def compare(kind,f,index,x,y,numeric=False,ledger=False):
 global first_discrete,first_numeric,first_ledger
 if x==y:return True
 z=dict(kind=kind,fixture=f,index=index,left=x,right=y)
 if numeric:
  if first_numeric is None:first_numeric=z
  if ledger and first_ledger is None:first_ledger=z
  return isinstance(x,(float,int)) and isinstance(y,(float,int)) and math.isfinite(x) and math.isfinite(y) and abs(x-y)<=1e-4+1e-4*abs(y)
 if first_discrete is None:first_discrete=z
 return False
ids=[f['id'] for f in json.loads((D/'stageA-inputs.json').read_text())['fixtures']]
for fid in ids:
 a=next((x for x in raw['rows'] if x['fixture_id']==fid and x['engine']=='candidate'),None);b=next((x for x in raw['rows'] if x['fixture_id']==fid and x['engine']=='reference'),None);okay=bool(a and b and not a['primary'] and not b['primary']);max_prior=0;max_score=0;max_ledger=0
 if okay:
  okay &= compare('CP_count',fid,0,len(a['CPs']),len(b['CPs'])) and len(a['CPs'])==32
  for k,(x,y) in enumerate(zip(a['CPs'],b['CPs']),1):
   for n in ['action','root_visits','simulations','nn_calls']:okay &= compare('CP_'+n,fid,k,x[n],y[n])
   for n in ['root_mean','root_valueSum']:okay &= compare('CP_'+n,fid,k,x[n],y[n],True,True);max_ledger=max(max_ledger,abs(x[n]-y[n]))
   okay &= compare('edge_count',fid,k,len(x['root_edges']),len(y['root_edges']))
   for j,(xx,yy) in enumerate(zip(x['root_edges'],y['root_edges'])):
    for z,n in [(0,'Action'),(2,'visits')]:okay &= compare('edge_'+n,fid,[k,j],xx[z],yy[z])
    for z,n in [(1,'prior'),(3,'sum')]:okay &= compare('edge_'+n,fid,[k,j],xx[z],yy[z],True,z==3)
    max_prior=max(max_prior,abs(xx[1]-yy[1]));max_ledger=max(max_ledger,abs(xx[3]-yy[3]))
  okay &= compare('NN_count',fid,0,len(a['numeric']),len(b['numeric']))
  for j,(x,y) in enumerate(zip(a['numeric'],b['numeric'])):
   for n in ['key','ply','turn','features_bits','legal','path','node_index','NN_bits']:okay &= compare('NN_'+n,fid,j,x[n],y[n])
   okay &= compare('NN_history',fid,j,sorted(x['history']),sorted(y['history']))
  for n in ['selects','backups']:
   aa=a['trace'][n];bb=b['trace'][n];okay &= compare(n+'_length',fid,0,len(aa),len(bb))
   for j,(x,y) in enumerate(zip(aa,bb)):
    for key in x:
     if key=='updates':
      okay &= compare('updates_length',fid,j,len(x[key]),len(y[key]))
      for u,(xx,yy) in enumerate(zip(x[key],y[key])):
       for v in ['index','preN']:okay &= compare('backup_'+v,fid,[j,u],xx[v],yy[v])
       for v in ['preSum','value']:okay &= compare('backup_'+v,fid,[j,u],xx[v],yy[v],True,True)
     else:
      numeric=key in ['nodeSum','parentQ','visited_base_prior_sum','prior','childSum','childQ','score','value_leaf_side']
      okay &= compare(n+'_'+key,fid,j,x[key],y.get(key),numeric,key in ['nodeSum','childSum','value_leaf_side'])
      if key=='score':max_score=max(max_score,abs(x[key]-y[key]))
  okay &= compare('terminal_noNN',fid,0,a['terminal_noNN'],b['terminal_noNN'])
 pairs.append({'fixture':fid,'finite_supported':bool(okay),'CPs':len(a['CPs']) if a else 0,'NN':len(a['numeric']) if a else 0,'max_prior_difference':max_prior,'max_score_difference':max_score,'max_ledger_difference':max_ledger})
old=json.loads((R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs/port151-stageA-r2/browser-result.json').read_text());cross=[]
for fid in ids:
 a=next((x for x in raw['rows'] if x['fixture_id']==fid and x['engine']=='candidate'),None);b=next(x for x in old['rows'] if x['fixture_id']==fid and x['engine']=='candidate')
 if not a or not a['numeric']:continue
 x=a['numeric'][0];y=b['numeric'][0];left=x['policy_logits']+[x['value']];right=y['policy_logits']+[y['value']];first=next(({'index':i,'native':xx,'old_Wasm':yy,'delta':xx-yy} for i,(xx,yy) in enumerate(zip(left,right)) if xx!=yy),None)
 cross.append({'fixture':fid,'input_bits_exact':x['features_bits']==y['features_bits'],'different_f32_count':sum(xx!=yy for xx,yy in zip(left,right)),'first_difference':first,'max_abs_difference':max(abs(xx-yy) for xx,yy in zip(left,right)),'compatibility_abs1e4_rel1e4':all(abs(xx-yy)<=1e-4+1e-4*abs(yy) for xx,yy in zip(left,right)),'providers_differ':True,'no_crossbackend_discrete_claim':True})
passed=len(raw['rows'])==10 and all(x['finite_supported'] for x in pairs) and not raw['errors'] and first_discrete is None
out={'issue':'quoridor-4lc.165','run':run,'raw_SHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'StageA_finite_supported':passed,'StageB_allowed':passed,'first_discrete_difference':first_discrete,'first_numeric_difference':first_numeric,'first_ledger_difference':first_ledger,'pairs':pairs,'native_vs_old_Wasm_root_only':cross,'hand_NN':raw['hand_NN'],'startup_NN':raw['startup_NN'],'sameK_not_sameCPU_or_strength':True,'ledger_floating_not_mislabeled_discrete':True}
(D/(run+'-analysis.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert passed,'MECHANISM_NOT_SUPPORTED'
