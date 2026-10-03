"""Stopped StageA exact discrete pairing; tolerances never excuse a path difference."""
import json,hashlib,math,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/151-sigma-web-port';run=sys.argv[1];path=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs'/run/'browser-result.json';raw=json.loads(path.read_text());pairs=[];first_numeric=None;first_discrete=None

def discrepancy(kind,fixture,index,left,right,numeric=False):
 global first_numeric,first_discrete
 if left==right:return True
 record={'kind':kind,'fixture':fixture,'index':index,'left':left,'right':right}
 if numeric:
  if first_numeric is None:first_numeric=record
  return isinstance(left,(int,float)) and isinstance(right,(int,float)) and math.isfinite(left) and math.isfinite(right) and abs(left-right)<=1e-4+1e-4*abs(right)
 if first_discrete is None:first_discrete=record
 return False
rows=raw['rows'];ids=list(dict.fromkeys(r['fixture_id'] for r in rows))
for fid in ids:
 a=next((r for r in rows if r['fixture_id']==fid and r['engine']=='candidate'),None);b=next((r for r in rows if r['fixture_id']==fid and r['engine']=='reference'),None);okay=bool(a and b and not a['primary'] and not b['primary']);compared={'fixture':fid,'okay':okay}
 if not okay:pairs.append(compared);continue
 assert len(a['CPs'])==len(b['CPs'])==32
 max_prior_diff=max_score_diff=0
 for k,(x,y) in enumerate(zip(a['CPs'],b['CPs']),1):
  okay &= discrepancy('CP_Action',fid,k,x['action'],y['action'])
  okay &= discrepancy('root_count',fid,k,x['root_visits'],y['root_visits'])
  okay &= discrepancy('root_ledger',fid,k,x['root_valueSum'],y['root_valueSum'])
  okay &= discrepancy('root_mean',fid,k,x['root_mean'],y['root_mean'])
  for j,(ea,eb) in enumerate(zip(x['root_edges'],y['root_edges'])):
   for z,n in [(0,'edge_Action_order'),(2,'edge_visits'),(3,'child_valueSum')]:okay &= discrepancy(n,fid,[k,j],ea[z],eb[z])
   okay &= discrepancy('root_prior',fid,[k,j],ea[1],eb[1],True);max_prior_diff=max(max_prior_diff,abs(ea[1]-eb[1]))
  okay &= discrepancy('root_edge_count',fid,k,len(x['root_edges']),len(y['root_edges']))
 okay &= discrepancy('NN_completed_count',fid,0,len(a['numeric']),len(b['numeric']))
 for j,(x,y) in enumerate(zip(a['numeric'],b['numeric'])):
  for n in ['key','ply','turn','features_bits','legal','path','policy_logits','value']:okay &= discrepancy('request_'+n,fid,j,x[n],y[n])
  okay &= discrepancy('request_history',fid,j,sorted(x['history']),sorted(y['history']))
 for n in ['selects','backups']:
  x=a['trace'][n];y=b['trace'][n];okay &= discrepancy(n+'_length',fid,0,len(x),len(y))
  for j,(sx,sy) in enumerate(zip(x,y)):
   for key in sx:
    okay &= discrepancy(n+'_'+key,fid,j,sx[key],sy.get(key),n=='selects' and key in ['score','prior','visited_base_prior_sum'])
    if key=='score':max_score_diff=max(max_score_diff,abs(sx[key]-sy[key]))
 okay &= discrepancy('terminal_noNN',fid,0,a['terminal_noNN'],b['terminal_noNN'])
 compared.update(okay=bool(okay),root_CPs=32,requests=len(a['numeric']),selects=len(a['trace']['selects']),all_path_and_order_visits_Action_ledger_exact=bool(okay),max_prior_difference=max_prior_diff,max_score_difference=max_score_diff,cap_refusal=a['cp']['guard_refusal'],same_backend_saved_NN_exact=True)
 pairs.append(compared)
passed=len(rows)==10 and len(pairs)==5 and all(x['okay'] for x in pairs) and not raw['errors']
out={'issue':'quoridor-4lc.151','run':run,'source_raw_SHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'StageA_finite_supported':passed,'first_numeric_difference':first_numeric,'first_discrete_difference':first_discrete,'pairs':pairs,'StageB_allowed':passed,'sameK_not_sameCPU':True,'not_general_deep_or_formal_Sigma_proof':True,'NN_actual':raw['hand_NN'],'startup_separate':6}
(D/(run+'-analysis.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert passed,'STAGEA_DISCRETE_OR_NUMERIC_NOT_SUPPORTED'
