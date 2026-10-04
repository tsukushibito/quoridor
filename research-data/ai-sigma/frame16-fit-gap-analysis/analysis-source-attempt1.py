"""NN0 matched residual decomposition, predefined label-free subgroups."""
from pathlib import Path
import json,gzip,math,collections,csv
D=Path('research-data/ai-sigma/frame16-fit-gap-analysis');rows=[json.loads(x)for x in gzip.open(D/'per-row.jsonl.gz','rt')];assert len(rows)==5901 and set(r['split']for r in rows)=={'train','validation'};names=list(rows[0]['NN'])
def summarize(q,name,planned):
 by=collections.defaultdict(list)
 for r in q:by[r['group']].append(r)
 n=len(q);G=len(by);s=dict(rows=n,games=G,planned_games=planned,zero_selected_games=planned-G,primary_rows=n,game_equal_conditional=True)
 if not G:return s
 weighted=[(r,1/(G*len(g)))for g in by.values()for r in g]
 e=lambda r:r['rootmean']-r['distance'];a=lambda r:r['NN'][name]-r['distance']
 mean=lambda f:sum(w*f(r)for r,w in weighted)
 de=mean(e);da=mean(a);ve=mean(lambda r:(e(r)-de)**2);va=mean(lambda r:(a(r)-da)**2);cross=mean(lambda r:e(r)*a(r));cov=mean(lambda r:(e(r)-de)*(a(r)-da));Derr=mean(lambda r:e(r)**2);Nerr=mean(lambda r:(a(r)-e(r))**2);disp=mean(lambda r:a(r)**2);delta=disp-2*cross;assert abs(Nerr-Derr-delta)<1e-12
 pg={g:dict(rows=len(rs),distance_MSE=sum(e(r)**2 for r in rs)/len(rs),NN_MSE=sum((a(r)-e(r))**2 for r in rs)/len(rs))for g,rs in by.items()}
 signs=[(r,w)for r,w in weighted if abs(e(r))>1e-12 and abs(a(r))>1e-12];zs=[(r,w)for r,w in weighted if r['z']is not None];zsign=[(r,w)for r,w in zs if r['z']!=0]
 s.update(distance_gameMSE=Derr,NN_gameMSE=Nerr,delta_NN_minus_D=delta,NN_rowMSE=sum((a(r)-e(r))**2 for r in q)/n,distance_rowMSE=sum(e(r)**2 for r in q)/n,eD_mean=de,rNN_mean=da,eD_RMS=math.sqrt(Derr),rNN_RMS=math.sqrt(disp),residual_prediction_MSE=Nerr,displacement_MSE=disp,alignment_cross_E_eD_rNN=cross,error_delta_decomposition='E[rNN^2]-2E[eD*rNN]',weighted_centered_correlation=cov/math.sqrt(ve*va)if ve*va>0 else None,regression_slope_rNN_on_eD=cov/ve if ve>0 else None,sign_agreement_weighted=sum(w*(e(r)*a(r)>0)for r,w in signs)/sum(w for r,w in signs)if signs else None,sign_valid_rows=len(signs),gain_games=sum(v['NN_MSE']<v['distance_MSE']for v in pg.values()),loss_games=sum(v['NN_MSE']>v['distance_MSE']for v in pg.values()),per_game=pg,NN_z_MSE_gameweighted=sum(w*(r['NN'][name]-r['z'])**2 for r,w in zs)/sum(w for r,w in zs)if zs else None,distance_z_MSE_gameweighted=sum(w*(r['distance']-r['z'])**2 for r,w in zs)/sum(w for r,w in zs)if zs else None,z_sign_gameweighted=sum(w*(r['NN'][name]*r['z']>0)for r,w in zsign)/sum(w for r,w in zsign)if zsign else None,z_valid_rows=len(zs))
 return s
result=dict(target='rootmean STM',units='all primary MSE game-equal within selected subset; rowMSE separately',group_selection='label-free fixed groups; multiple subgroup summaries exploratory',splits={},subgroups={},NN_added=0)
for split,planned in [('train',96),('validation',24)]:
 q=[r for r in rows if r['split']==split];result['splits'][split]={n:summarize(q,n,planned)for n in names}
 result['subgroups'][split]={}
 global_count=collections.Counter(r['group']for r in q)
 global_weight=lambda r:1/(planned*global_count[r['group']])
 result.setdefault('global_weight_bin_contributions',{})[split]={}
 for dim in ['cohort','phase','self_bin','opponent_bin','difference_bin','walls_bin','distance_clip']:
  result['subgroups'][split][dim]={str(v):{n:summarize([r for r in q if r[dim]==v],n,planned)for n in names}for v in sorted(set(r[dim]for r in q))}
  parts={}
  for v in sorted(set(r[dim]for r in q)):
   subset=[r for r in q if r[dim]==v];mass=sum(global_weight(r)for r in subset);parts[str(v)]={'weightmass':mass,'rows':len(subset),'games':len(set(r['group']for r in subset)),'models':{}}
   for n in names:
    disp=sum(global_weight(r)*(r['NN'][n]-r['distance'])**2 for r in subset)
    cross=sum(global_weight(r)*(r['rootmean']-r['distance'])*(r['NN'][n]-r['distance'])for r in subset)
    parts[str(v)]['models'][n]={'global_displacement_contribution':disp,'global_alignment_cross':cross,'global_signed_gap_contribution':disp-2*cross,'original_rowweight':"1/(split_G * fullgame_nrows)"}
  assert abs(sum(v['weightmass']for v in parts.values())-1)<1e-12
  for n in names:assert abs(sum(v['models'][n]['global_signed_gap_contribution']for v in parts.values())-result['splits'][split][n]['delta_NN_minus_D'])<1e-12
  result['global_weight_bin_contributions'][split][dim]=parts
(D/'residual-analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
with (D/'matched-comparison.csv').open('w')as f:
 w=csv.DictWriter(f,fieldnames=['split','checkpoint','rows','games','distance_gameMSE','NN_gameMSE','delta_NN_minus_D','NN_rowMSE','distance_rowMSE','rNN_RMS','weighted_centered_correlation','gain_games','loss_games']);w.writeheader()
 for split,mm in result['splits'].items():
  for name,s in mm.items():w.writerow(dict(split=split,checkpoint=name,**{k:s[k]for k in w.fieldnames if k not in ['split','checkpoint']}))
print(json.dumps({split:{n:{k:s[k]for k in ['NN_gameMSE','distance_gameMSE','delta_NN_minus_D','weighted_centered_correlation','rNN_RMS','gain_games','loss_games']}for n,s in mm.items()}for split,mm in result['splits'].items()}))
