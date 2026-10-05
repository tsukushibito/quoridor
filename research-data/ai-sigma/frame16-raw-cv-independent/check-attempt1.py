"""Independent NN0, only selected full ridge equation; never import producer/model."""
import os,time,json,gzip,lzma,hashlib,struct,collections,pathlib,resource,datetime
os.sched_setaffinity(0,{0})
import numpy as np
D=pathlib.Path('research-data/ai-sigma/frame16-raw-cv-independent'); S=pathlib.Path('research-data/ai-sigma/frame16-fit-gap-analysis/raw-cv-control'); start=time.monotonic(); bindings={}
def load(p):
 p=pathlib.Path(p); b=p.read_bytes();bindings[str(p)]=hashlib.sha256(b).hexdigest()
 if p.suffix=='.xz': b=lzma.decompress(b)
 if p.suffix=='.gz': b=gzip.decompress(b)
 return json.loads(b)
def lines(p):
 p=pathlib.Path(p);b=p.read_bytes();bindings[str(p)]=hashlib.sha256(b).hexdigest();b=lzma.decompress(b) if p.suffix=='.xz' else gzip.decompress(b);return [json.loads(v)for v in b.splitlines()]
def close(a,b,tol=1e-12):assert abs(float(a)-float(b))<=tol,(a,b,tol)
reg=load(S/'preregister.json'); c=load(S/'coefficients-and-folds.json.xz'); owner=load(S/'result.json.xz'); archive=load(S/'archive-manifest.json')
stage=load(reg['stage']); mask=load(stage['mask']); labs=lines(stage['training_labels']); L={r['id']:r for r in labs};assert len(L)==len(labs)==5901 and all(r['split'] in ('train','validation')for r in labs)
# Test label-free rows excluded before all joins or calibration.
meta=[]
for m in lines(stage['metadata']):
 if m['split']=='test':continue
 if m['split']=='train' and m['group'] not in stage['train_groups']:continue
 if m['split']=='validation' and not mask['rows'][m['id']]['primary_eligible']:continue
 meta.append(m)
assert len(meta)==5901 and len(set(m['id']for m in meta))==5901
old=lines('research-data/ai-sigma/frame16-fit-gap-analysis/residual-head-control/comparison-per-row.jsonl.gz');oldby={r['id']:r for r in old};assert len(oldby)==5901
full=lines(S/'full-predictions.jsonl.xz');oof=lines(S/'OOF-predictions.jsonl.xz');P={r['id']:r for r in full};O={r['id']:r for r in oof};assert len(P)==len(full)==5901 and len(O)==len(oof)==4653
X=np.zeros((5901,626)); signs=[];keys=[]
for i,m in enumerate(meta):
 side=m['side']-1;assert side in (0,1); ids=[sorted(m['ids'][side]),sorted(m['ids'][1-side])]; bits=[struct.unpack('<I',struct.pack('<f',v))[0]for v in m['distance']]
 sig=hashlib.sha256(json.dumps(['QF1-f32-STM-v1',*ids,bits],separators=(',',':')).encode()).hexdigest();assert sig==m['QF1_input_sha256'],m['id'];keys.append((m['state_key'],m['history_key'],sig))
 for v in range(2):assert len(ids[v])==len(set(ids[v])) and all(0<=j<312 for j in ids[v]);X[i,[312*v+j for j in ids[v]]]=1
 X[i,624:]=[struct.unpack('<f',struct.pack('<I',v))[0]for v in bits]
 assert L[m['id']]['split']==m['split']; r=oldby[m['id']];close(r['rootmean'],L[m['id']]['rootmean']);assert r['z']==L[m['id']]['z'] and r['side']==m['side'] and r['group']==m['group']
y=np.array([L[m['id']]['rootmean']for m in meta]); z=np.array([L[m['id']]['z'] for m in meta],float); tr=np.array([m['split']=='train'for m in meta]);assert tr.sum()==4653
fold=np.array([reg['game_folds'].get(m['group'],-1)for m in meta]); assert (fold[~tr]==-1).all()
byco=collections.defaultdict(set)
for m in meta:
 if m['split']=='train':byco[m['cohort']].add(m['group'])
reconstructed={}
for co,gs in byco.items():
 ordered=sorted(gs,key=lambda g:hashlib.sha256(('frame16-216-CV-v1\0'+g).encode()).hexdigest())
 assert ordered==reg['fold_cohort_order'][co]
 reconstructed.update({g:j%5 for j,g in enumerate(ordered)})
assert reconstructed==reg['game_folds']
for key in ('family','game_id'):
 seen=collections.defaultdict(set)
 for i,m in enumerate(meta):
  if tr[i]:seen[m[key]].add(int(fold[i]))
 assert all(len(v)==1 for v in seen.values())
def weight(ix):
 counts=collections.Counter(meta[i]['group']for i in ix);return np.array([1/(len(counts)*counts[meta[i]['group']])for i in ix]),len(counts)
def baseline(ix):
 w,G=weight(ix);s=X[ix,625]-X[ix,624];u=float(w@s);v=float(w@y[ix]);var=float(w@((s-u)**2));b=float(w@((s-u)*(y[ix]-v)))/var if var>0 else 0.;a=v-b*u
 p=np.clip(np.float32(a)+np.float32(b)*(X[:,625].astype('f4')-X[:,624].astype('f4')),-1,1);return p,dict(a=a,b=b,variance=var,groups=G)
def moments(ix):
 w,G=weight(ix);mu=np.sum(X[ix]*w[:,None],axis=0);var=np.sum((X[ix]-mu)**2*w[:,None],axis=0);zero=var<=0;mu=mu.astype('f4');std=np.sqrt(var).astype('f4');safe=std.copy();safe[zero]=1;Z=(X.astype('f4')-mu)/safe;Z[:,zero]=0
 return Z,mu,std,zero
foldchecks=[];exposures=[];oofbase=np.zeros(4653);trainix=np.where(tr)[0]; ti={i:j for j,i in enumerate(trainix)}
for k in range(5):
 fit=np.where(tr&(fold!=k))[0];held=np.where(tr&(fold==k))[0];bp,bc=baseline(fit);Z,mu,sd,zero=moments(fit);saved=c['fold_pipeline'][k]
 for f in ('a','b','variance'):close(bc[f],saved['baseline'][f],1e-12)
 assert np.array_equal(mu,np.array(saved['moments']['mu_f32'],'f4')) and np.array_equal(sd,np.array(saved['moments']['sigma_f32'],'f4'));assert np.where(zero)[0].tolist()==saved['moments']['zero_columns']
 for i in held:
  o=O[meta[i]['id']];assert o['group']==meta[i]['group'] and o['fold']==k;close(bp[i],o['foldD'],1e-7);oofbase[ti[i]]=o['foldD']
 sets=[{keys[i][j]for i in fit}for j in range(3)];shared=[i for i in held if any(keys[i][j]in sets[j]for j in range(3))];counts=collections.Counter(meta[i]['group']for i in held);pg={g:{'rows':n,'shared_rows':sum(meta[i]['group']==g for i in shared)}for g,n in counts.items()}
 exposures.append(dict(fold=k,rows=len(held),games=len(counts),shared_rows=len(shared),shared_original_OOF_mass=sum(1/(96*counts[meta[i]['group']])for i in shared),games_any_shared=sum(v['shared_rows']>0 for v in pg.values()),games_zero_unexposed=sum(v['rows']==v['shared_rows']for v in pg.values()),pergame=pg))
 unseen=(X[fit,:624].sum(0)==0)&(X[held,:624].sum(0)>0);has=(X[held,:624][:,unseen]>0).any(1);wh,G=weight(held)
 assert np.where(unseen)[0].tolist()==saved['unseen_active_columns'];close(wh@has,saved['unseen_rowmass_within_fold'])
 foldchecks.append(dict(fold=k,groups=G,rows=len(held),unseen_active_columns=int(unseen.sum()),unseen_rowmass=float(wh@has)))
assert [q['groups']for q in foldchecks]==[24,18,18,18,18]
def metric(ix,p,base):
 w,G=weight(ix);e=y[ix]-base[ix];r=p[ix]-base[ix];pg={}
 for g in sorted({meta[i]['group']for i in ix}):
  jj=np.array([i for i in ix if meta[i]['group']==g]);pg[g]=dict(rows=len(jj),model=float(np.mean((p[jj]-y[jj])**2)),distance=float(np.mean((base[jj]-y[jj])**2)))
 sign=lambda a:float(w@((a[ix]*z[ix])>0));out=dict(rows=len(ix),games=G,gameMSE=float(w@((p[ix]-y[ix])**2)),rowMSE=float(np.mean((p[ix]-y[ix])**2)),DgameMSE=float(w@(e**2)),DrowMSE=float(np.mean(e**2)),displacement=float(w@(r*r)),alignment=float(w@(e*r)),zgameMSE=float(w@((p[ix]-z[ix])**2)),DzgameMSE=float(w@((base[ix]-z[ix])**2)),zsign=sign(p),Dzsign=sign(base),hard_saturated_rows=int((np.abs(p[ix])>=1).sum()),gain_games=sum(v['model']<v['distance']for v in pg.values()),loss_games=sum(v['model']>v['distance']for v in pg.values()),pergame=pg)
 close(out['gameMSE']-out['DgameMSE'],out['displacement']-2*out['alignment']);out['bins']={}
 for dim in ('phase','cohort','walls_bin'):
  vals=[str(oldby[meta[i]['id']][dim])for i in ix];bins={}
  for v in sorted(set(vals)):
   pick=np.array([j for j,t in enumerate(vals)if t==v]);bins[v]=dict(rows=len(pick),games=len({meta[ix[j]]['group']for j in pick}),mass=float(w[pick].sum()),signedgap=float(w[pick]@((p[ix[pick]]-y[ix[pick]])**2-e[pick]**2)))
  close(sum(q['signedgap']for q in bins.values()),out['gameMSE']-out['DgameMSE']);out['bins'][dim]=bins
 return out
OOF={};wb,_=weight(trainix)
for lam in ('0.01','1.0','100.0'):
 p=np.zeros(5901);bp=np.zeros(5901);p[tr]=[O[m['id']]['pred'][lam]for m in meta if m['split']=='train'];bp[tr]=oofbase;mt=metric(trainix,p,bp);OOF[lam]=mt;close(mt['gameMSE'],owner['selection']['OOF_gameMSE'][lam]);close(mt['rowMSE'],owner['OOF'][lam]['rowMSE'])
 for g,v in mt['pergame'].items():close(v['model'],owner['OOF'][lam]['pergame'][g]['MSE']);close(v['distance'],owner['OOF'][lam]['pergame'][g]['baselineMSE'])
minimum=min(q['gameMSE']for q in OOF.values());chosen=max(float(l)for l,q in OOF.items()if q['gameMSE']<=minimum+1e-10);assert chosen==c['selection']['selected_lambda']==owner['selection']['selected_lambda'];assert owner['selection']['val_used'] is False
base,bc=baseline(trainix);Z,mu,sd,zero=moments(trainix)
for f in ('a','b','variance'):close(bc[f],c['fullbaseline'][f])
assert np.array_equal(mu,np.array(c['fullmoments']['mu_f32'],'f4')) and np.array_equal(sd,np.array(c['fullmoments']['sigma_f32'],'f4'));assert np.where(zero)[0].tolist()==c['fullmoments']['zero_columns']
F=np.column_stack((np.ones(5901),Z.astype(float)));w,G=weight(trainix);A=F[trainix].T@(w[:,None]*F[trainix]);A[np.arange(1,627),np.arange(1,627)]+=chosen;rhs=F[trainix].T@(w*(y[trainix]-base[trainix].astype(float)));coef=np.array(c['fullfit']['coefficients_f64']);normal=float(np.max(np.abs(A@coef-rhs)));assert normal<1e-9
sol=np.linalg.solve(A,rhs);coeffmax=float(np.max(np.abs(sol-coef)));assert coeffmax<1e-10
applied=np.array(c['fullfit']['applied_f32'],'f4');assert np.array_equal(coef.astype('f4'),applied)
unclip=(base+(applied[0]+Z@applied[1:]).astype('f4')).astype('f4');pred=np.clip(unclip,-1,1);savedpred=np.array([P[m['id']]['selected_raw']for m in meta]);pdiff=float(np.max(np.abs(pred-savedpred)));assert pdiff<=1e-6
metrics={}
for split in ('train','validation'):
 ix=np.where(np.array([m['split']==split for m in meta]))[0];q=metric(ix,savedpred,base.astype(float));metrics[split]=q;own=owner['fullmetrics'][split]['selected_raw']
 for a,b in [('gameMSE','NN_gameMSE'),('rowMSE','NN_rowMSE'),('DgameMSE','distance_gameMSE'),('zgameMSE','NN_z_MSE_gameweighted'),('DzgameMSE','distance_z_MSE_gameweighted'),('zsign','z_sign_gameweighted'),('displacement','displacement_MSE'),('alignment','alignment_cross_E_eD_rNN')]:close(q[a],own[b])
 assert q['games']==(96 if split=='train'else24)
sets=[{keys[i][j]for i in trainix}for j in range(3)];valix=np.where(~tr)[0];valshared=[i for i in valix if any(keys[i][j]in sets[j]for j in range(3))]
# Read owner exposure only after independently recomputing.
exowner=load(S/'exposure.json');assert [q['shared_rows']for q in exposures]==[q['shared_rows']for q in exowner['folds']];assert len(valshared)==exowner['fixed_validation']['shared_rows']
result=dict(status='PASS',issue='quoridor-4lc.219',UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),NN_added=0,old217cap=180,new219cap=120,source_read_charge=60,calc_charge=60,rows=5901,train_games=96,validation_games=24,foldchecks=foldchecks,OOF=OOF,selected_lambda=chosen,fullfit=dict(normal_residual=normal,coeffmaxdiff=coeffmax,predmaxdiff=pdiff,zero_columns=int(zero.sum()),only_fullfit_solved=True,15_foldfits_recalculated=False),metrics=metrics,exposure=dict(folds=exposures,validation_shared_rows=len(valshared),post_result_exclusions=0),bindings=bindings,actual_wall=time.monotonic()-start,peak_RSS=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,limits=['opaque history','recorded family only','teacher truth not recertified','single partition','reused validation','phase3 independently unverified','no test read'])
assert result['peak_RSS']<469762048;assert result['actual_wall']<60
(D/'result.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n');print(json.dumps({k:result[k]for k in ('status','selected_lambda','fullfit','actual_wall','peak_RSS')}))
