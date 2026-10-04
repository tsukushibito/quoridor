"""Independent stdlib NN0 saved arithmetic; never import producer or a model."""
from pathlib import Path
import json,gzip,struct,math,bisect,collections,hashlib,time,datetime,os,resource
os.sched_setaffinity(0,{0});start=time.monotonic()
D=Path('research-data/ai-sigma/frame16-fit-gap-independent');S=Path('research-data/ai-sigma/frame16-fit-gap-analysis')
J=lambda p:json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def lines(p):
 with gzip.open(p,'rt')as f:
  for l in f:yield json.loads(l)
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
reg=J(S/'preregister.json');stage=J(reg['stage']);spec=J(S/'group-spec.json');parity=J(S/'finite-parity.json');stop=J(S/'science-stop.json');fit=J('research-data/ai-sigma/frame14-representation-audit/result.json')['fit']
assert sha(reg['stage'])==reg['stage_SHA']
bind={}
for k,h in reg['source_bindings'].items():
 assert sha(k)==h,k
 bind[k]=h
for name,a in reg['artifacts'].items():assert sha(a['path'])==a['SHA'],name
for k in ['metadata','mask','training_labels']:assert sha(stage[k])==stage[k+'_sha256'],k
assert reg['coefficients']==dict(a=fit['a'],b=fit['b']) and reg['constant']==fit['constant_train_gameequal']
mask=J(stage['mask'])['rows'];meta={}
for m in lines(stage['metadata']):
 # Reject oldtest before join/analysis; label-free container only.
 if m['split']=='test':continue
 if m['split']=='train' and m['group']not in stage['train_groups']:continue
 if m['split']=='validation' and not mask[m['id']]['primary_eligible']:continue
 assert m['id']not in meta;meta[m['id']]=m
labels={l['id']:l for l in lines(stage['training_labels'])};rows=list(lines(S/'per-row.jsonl.gz'))
assert len(rows)==5901 and set(r['id']for r in rows)==set(meta) and len(set(r['id']for r in rows))==5901
counts=collections.Counter((m['split'],m['group'])for m in meta.values());assert sum(n for (s,g),n in counts.items()if s=='train')==4653 and sum(n for (s,g),n in counts.items()if s=='validation')==1248
assert sum(s=='train'for s,g in counts)==96 and sum(s=='validation'for s,g in counts)==24
edges={};train=[m for m in meta.values()if m['split']=='train']
for key,idx in [('self',0),('opponent',1),('difference',2)]:
 vals=[]
 for m in train:
  ds=[f32(x)for x in m['distance']];v=[ds[0],ds[1],ds[1]-ds[0]][idx];vals.append((v,1/(96*counts[('train',m['group'])])))
 vals.sort();selected=[]
 for quantile in [.2,.4,.6,.8]:
  total=0
  for v,w in vals:
   total+=w
   if total>=quantile:selected.append(v);break
 edges[key]=sorted(set(selected))
assert edges==spec['distance_edges']
maxD=0
for r in rows:
 m=meta[r['id']];l=labels[r['id']]
 for k in ['group','split','cohort','ply','side']:assert r[k]==m[k],(r['id'],k)
 assert r['rootmean']==l['rootmean']and r['z']==l['z'] and r['split']==l['split']
 assert mask[r['id']]['primary_eligible']
 ds=[f32(x)for x in m['distance']];delta=ds[1]-ds[0]
 assert [r['self_distance'],r['opponent_distance']]==ds and r['distance_difference']==delta
 direct=max(-1,min(1,f32(f32(fit['a'])+f32(f32(fit['b'])*f32(delta)))))
 maxD=max(maxD,abs(direct-r['distance']));assert abs(direct-r['distance'])<1e-7
 assert r['constant']==reg['constant'];assert r['phase']==('early'if m['ply']<40 else'middle'if m['ply']<100 else'late')
 ids=m['ids'][m['side']-1];a=[x-290 for x in ids if 290<=x<=300];b=[x-301 for x in ids if 301<=x<=311];placed=sum(162<=x<290 for x in ids)
 assert len(a)==len(b)==1 and placed+a[0]+b[0]==20
 assert r['walls_total']==20-a[0]-b[0] and r['walls_bin']==min(3,r['walls_total']//5)
 for field,key,v in [('self_bin','self',ds[0]),('opponent_bin','opponent',ds[1]),('difference_bin','difference',delta)]:assert r[field]==bisect.bisect_right(edges[key],v)
 assert r['distance_clip']==('saturated'if abs(r['distance'])==1 else'unsaturated')
 assert all(math.isfinite(v)for v in [r['rootmean'],r['z'],r['distance'],*r['NN'].values()])
models=['plain200','plain400','standard200','standard400'];dims={'cohort':['opening-'+str(x)for x in [8,12,16,20,24,28]],'phase':['early','middle','late'],'self_bin':range(5),'opponent_bin':range(5),'difference_bin':range(5),'walls_bin':range(4),'distance_clip':['saturated','unsaturated']}
out={'issue':'quoridor-4lc.217','PASS':True,'basis':'saved predictions only; independent scalar arithmetic, no forward authentication','rows':5901,'counts':{'train':4653,'validation':1248},'groups':{'train':96,'validation':24},'distance_maxabs':maxD,'edges_train_only':edges,'splits':{},'bins':{},'inputSHA':{},'bindings':bind}
owner=J(S/'residual-analysis.json');maxdiff=0
for split,G in [('train',96),('validation',24)]:
 q=[r for r in rows if r['split']==split];weight=lambda r:1/(G*counts[(split,r['group'])]);mean=lambda fn:math.fsum(weight(r)*fn(r)for r in q)
 names=['constant','distance']+models
 def pred(r,n):return r['NN'][n]if n in models else r[n]
 metrics={}
 for n in names:
  pgs={g:{'rows':counts[(split,g)],'rootmeanMSE':math.fsum((pred(r,n)-r['rootmean'])**2 for r in q if r['group']==g)/counts[(split,g)],'zMSE':math.fsum((pred(r,n)-r['z'])**2 for r in q if r['group']==g)/counts[(split,g)]}for ss,g in counts if ss==split}
  metrics[n]={'rootmean_gameMSE':mean(lambda r:(pred(r,n)-r['rootmean'])**2),'rootmean_rowMSE':math.fsum((pred(r,n)-r['rootmean'])**2 for r in q)/len(q),'z_gameMSE':mean(lambda r:(pred(r,n)-r['z'])**2),'z_rowMSE':math.fsum((pred(r,n)-r['z'])**2 for r in q)/len(q),'sign_game':mean(lambda r:float(pred(r,n)*r['z']>0)),'sign_row':sum(pred(r,n)*r['z']>0 for r in q)/len(q),'saturation_game':mean(lambda r:float(abs(pred(r,n))>=1)),'pergame':pgs}
 out['splits'][split]={'rows':len(q),'planned_games':G,'Gplus':G,'zeroeligible_games':0,'models':metrics,'decomposition':{}}
 for n in models:
  e=lambda r:r['rootmean']-r['distance'];rr=lambda r:pred(r,n)-r['distance'];disp=mean(lambda r:rr(r)**2);cross=mean(lambda r:e(r)*rr(r));gap=metrics[n]['rootmean_gameMSE']-metrics['distance']['rootmean_gameMSE'];mu_e=mean(e);mu_r=mean(rr);var_e=mean(lambda r:(e(r)-mu_e)**2);var_r=mean(lambda r:(rr(r)-mu_r)**2);cov=mean(lambda r:(e(r)-mu_e)*(rr(r)-mu_r))
  assert abs(gap-(disp-2*cross))<1e-12
  dec={'gap':gap,'displacement':disp,'cross':cross,'minus2cross':-2*cross,'e_mean':mu_e,'r_mean':mu_r,'r_RMS':math.sqrt(disp),'centered_corr':cov/math.sqrt(var_e*var_r)if var_e*var_r>0 else None,'variance_gap':var_r-2*cov,'meanbias_gap':mu_r**2-2*mu_e*mu_r,'gain_games':sum(metrics[n]['pergame'][g]['rootmeanMSE']<metrics['distance']['pergame'][g]['rootmeanMSE']for g in metrics[n]['pergame'])}
  assert abs(dec['variance_gap']+dec['meanbias_gap']-gap)<1e-12;out['splits'][split]['decomposition'][n]=dec
  own=owner['splits'][split][n]
  for val,key in [(gap,'delta_NN_minus_D'),(disp,'displacement_MSE'),(cross,'alignment_cross_E_eD_rNN')]:maxdiff=max(maxdiff,abs(val-own[key]));assert abs(val-own[key])<1e-12
  pm=parity['models'][n][split]['metrics']
  for k,pk in [('rootmean_gameMSE','rootmean_game_equal_mse'),('rootmean_rowMSE','rootmean_mse'),('z_gameMSE','z_game_equal_mse'),('z_rowMSE','z_mse')]:assert abs(metrics[n][k]-pm[pk])<1e-12
 out['bins'][split]={}
 for dim,values in dims.items():
  parts={}
  for v in values:
   sub=[r for r in q if r[dim]==v];part={'rows':len(sub),'games':len({r['group']for r in sub}),'mass':math.fsum(weight(r)for r in sub),'models':{}}
   for n in models:
    disp=math.fsum(weight(r)*(r['NN'][n]-r['distance'])**2 for r in sub);cross=math.fsum(weight(r)*(r['rootmean']-r['distance'])*(r['NN'][n]-r['distance'])for r in sub);gap=disp-2*cross
    part['models'][n]={'displacement':disp,'cross':cross,'signed_gap':gap}
    op=owner['global_weight_bin_contributions'][split][dim][str(v)];assert op['rows']==len(sub)and op['games']==part['games']and abs(op['weightmass']-part['mass'])<1e-12
    assert abs(gap-op['models'][n]['global_signed_gap_contribution'])<1e-12
   parts[str(v)]=part
  assert sum(p['rows']for p in parts.values())==len(q)and abs(math.fsum(p['mass']for p in parts.values())-1)<1e-12
  for n in models:assert abs(math.fsum(p['models'][n]['signed_gap']for p in parts.values())-out['splits'][split]['decomposition'][n]['gap'])<1e-12
  out['bins'][split][dim]=parts
assert parity['PASS']and parity['forward_samples']==stop['model_forward_samples']==23604 and stop['training_updates']==stop['test_forward']==0
for p in [S/'per-row.jsonl.gz',S/'preregister.json',S/'finite-parity.json',S/'science-stop.json',S/'group-spec.json',S/'analysis-spec.json',S/'analysis-version2.json',S/'analysis-attempt1.json.gz',S/'analysis-source-attempt1.py',S/'residual-analysis.json',S/'global-bin-reconciliation.json',Path('tools/ai-sigma-fit-gap-analysis/forward.py'),Path('tools/ai-sigma-fit-gap-analysis/analyze.py')]:out['inputSHA'][str(p)]=sha(p)
for p,h in out['inputSHA'].items():assert sha(p)==h,'immutable snapshot changed:'+p
out.update(owner_arithmetic_maxdiff=maxdiff,wall_seconds=time.monotonic()-start,peakRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,NN_added=0,test_read=0,charge_block_seconds=60,static_total_reserved=120,cap=180,remaining=60,UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
assert out['wall_seconds']<55 and out['peakRSS_bytes']<448*1024**2
(D/'result.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(json.dumps({s:{n:{k:v for k,v in d.items()if k in ['gap','displacement','cross','r_RMS','centered_corr','gain_games']}for n,d in t['decomposition'].items()}for s,t in out['splits'].items()}))
