"""217 remaining60: independent NN0 NPZ/normal equations/saved prediction arithmetic."""
from pathlib import Path
import json,gzip,struct,zipfile,ast,array,sys,os,math,collections,hashlib,time,resource,datetime
os.sched_setaffinity(0,{0});start=time.monotonic();D=Path('research-data/ai-sigma/frame16-fit-gap-independent');S=Path('research-data/ai-sigma/frame16-fit-gap-analysis/residual-head-control')
J=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
def rows(p):
 with gzip.open(p,'rt')as f:return [json.loads(l)for l in f]
old=rows('research-data/ai-sigma/frame16-fit-gap-analysis/per-row.jsonl.gz');q=rows(S/'comparison-per-row.jsonl.gz');reg=J(S/'preregister.json');amend=J(S/'preregister-amendment-v2.json');cf=J(S/'coefficients.json');df=J(S/'distance-reference-coefficients.json');stop=J(S/'science-stop.json');proc=J(S/'jobs/hidden-ridge-r1/process.json')
assert cf['model_weight_SHA']==J('research-data/ai-sigma/frame16-fit-gap-analysis/finite-parity.json')['checkpoints']['standard400']['weight_SHA']
assert len(q)==len(old)==5901 and reg['forward_added']==5901 and reg['lambda_fixed']==cf['lambda_fixed']==df['lambda_fixed']==.01
assert reg['intercept_penalty']==cf['intercept_penalty']==df['intercept_penalty']==0 and sha(reg['checkpoint'])==reg['checkpoint_SHA']
for p,h in reg['bindings'].items():assert sha(p)==h,p
assert sha(S/'preregister.json')==amend['main_preregister_SHA'] and sha('tools/ai-sigma-fit-gap-analysis/residual-head-control/distance_reference.py')==amend['source_SHA']
for a,b in zip(q,old):
 for k in b:
  if k=='NN':assert a['NN']['standard400']==b['NN']['standard400']
  else:assert a[k]==b[k],(a['id'],k)
 assert a['split']in ['train','validation']
count=collections.Counter((r['split'],r['group'])for r in q);tr=[i for i,r in enumerate(q)if r['split']=='train'];assert len(tr)==4653 and len(count)==120
w=[1/(96*count[('train',q[i]['group'])])for i in tr]
with zipfile.ZipFile(S/'hidden_features.npz')as z:
 def npy(name):
  with z.open(name)as f:
   head=f.read(8);assert head[:6]==b'\x93NUMPY';n=struct.unpack('<H'if head[6]==1 else'<I',f.read(2 if head[6]==1 else 4))[0];meta=ast.literal_eval(f.read(n).decode());assert not meta['fortran_order'];return meta,f.read()
 hm,hb=npy('hidden.npy');im,ib=npy('row_ids.npy');assert hm=={'descr':'<f4','fortran_order':False,'shape':(5901,32)} and im['shape']==(5901,)and im['descr'].startswith('<U')
 H=array.array('f');H.frombytes(hb)
 if sys.byteorder!='little':H.byteswap()
 width=int(im['descr'][2:])*4;ids=[ib[i:i+width].decode('utf-32-le').rstrip('\0')for i in range(0,len(ib),width)];assert ids==[r['id']for r in q]
mu=[math.fsum(w[j]*H[i*32+k]for j,i in enumerate(tr))for k in range(32)];var=[math.fsum(w[j]*(H[i*32+k]-mu[k])**2 for j,i in enumerate(tr))for k in range(32)];zero=[k for k,v in enumerate(var)if v<=0];mu32=list(map(f32,mu));sd32=[f32(math.sqrt(v))for v in var]
assert zero==cf['zero_columns'];assert max(abs(a-b)for a,b in zip(mu,cf['hidden_mean_f64']))<1e-12 and max(abs(a-b)for a,b in zip(var,cf['hidden_variance_f64']))<1e-12
assert mu32==cf['hidden_mean_f32']and sd32==cf['hidden_std_f32']
Z=[[0 if k in zero else f32(f32(H[i*32+k]-mu32[k])/sd32[k])for k in range(32)]for i in range(5901)]
e=[r['rootmean']-r['distance']for r in q]
def fit(features):
 n=len(features[0])+1;A=[[0.0]*n for _ in range(n)];rhs=[0.0]*n
 for jj,i in enumerate(tr):
  x=[1]+features[i];ww=w[jj]
  for j in range(n):
   v=ww*x[j];rhs[j]+=v*e[i]
   for k in range(j,n):A[j][k]+=v*x[k]
 for j in range(n):
  if j:A[j][j]+=.01
  for k in range(j):A[j][k]=A[k][j]
 M=[A[j][:]+[rhs[j]]for j in range(n)]
 for j in range(n):
  p=max(range(j,n),key=lambda k:abs(M[k][j]));M[j],M[p]=M[p],M[j];assert abs(M[j][j])>1e-14
  d=M[j][j];M[j]=[v/d for v in M[j]]
  for k in range(j+1,n):
   f=M[k][j]
   for l in range(j,n+1):M[k][l]-=f*M[j][l]
 beta=[0.0]*n
 for j in range(n-1,-1,-1):beta[j]=M[j][-1]-math.fsum(M[j][k]*beta[k]for k in range(j+1,n))
 err=max(abs(math.fsum(A[j][k]*beta[k]for k in range(n))-rhs[j])for j in range(n));assert err<1e-10
 return beta,err
beta,normal=fit(Z);coefdiff=max(abs(a-b)for a,b in zip(beta,cf['solve_coefficients_f64']));assert coefdiff<1e-8
ap=list(map(f32,beta));assert max(abs(a-b)for a,b in zip(ap,cf['applied_coefficients_f32']))<1e-7
s=[f32(r['opponent_distance']-r['self_distance'])for r in q];sm=math.fsum(w[j]*s[i]for j,i in enumerate(tr));sv=math.fsum(w[j]*(s[i]-sm)**2 for j,i in enumerate(tr));sm32=f32(sm);ss32=f32(math.sqrt(sv));sz=[[0.0 if sv<=0 else f32(f32(v-sm32)/ss32)]for v in s];db,dnormal=fit(sz)
assert abs(sm-df['mean_f64'])<1e-12 and abs(sv-df['var_f64'])<1e-12 and sm32==df['mean_f32']and ss32==df['std_f32']
assert max(abs(a-b)for a,b in zip(db,df['coefficients_f64']))<1e-10
bp=list(map(f32,db));maxhidden=0;maxdistance=0
for i,r in enumerate(q):
 residual=f32(ap[0]+f32(math.fsum(Z[i][k]*ap[k+1]for k in range(32))));u=f32(r['distance']+residual);p=max(-1,min(1,u));maxhidden=max(maxhidden,abs(u-r['ridge_unclipped']),abs(p-r['NN']['ridge']))
 dr=f32(bp[0]+f32(bp[1]*sz[i][0]));du=f32(r['distance']+dr);dp=max(-1,min(1,du));maxdistance=max(maxdistance,abs(du-r['distance_reference_unclipped']),abs(dp-r['NN']['distance_recalibration']))
assert maxhidden<1e-6 and maxdistance<1e-7
names=['distance','standard400','ridge','distance_recalibration'];out={'issue':'quoridor-4lc.217','phase2_PASS':True,'arrays':'NPZ/NPY scalar f32 independent; no numpy/torch/model import','lambda':.01,'train_only':True,'counts':{'train':4653,'validation':1248},'normal_residual':normal,'normal_coeff_maxdiff':coefdiff,'zero_columns':zero,'scalar_normal_residual':dnormal,'prediction_maxabs_hidden':maxhidden,'prediction_maxabs_distance':maxdistance,'splits':{},'bins':{},'inputSHA':{}}
owner=J(S/'comparison-summary.json');gameout={}
for split,G in [('train',96),('validation',24)]:
 rr=[r for r in q if r['split']==split];weight=lambda r:1/(G*count[(split,r['group'])]);mean=lambda fn:math.fsum(weight(r)*fn(r)for r in rr);metrics={};gameout[split]={}
 def pred(r,n):return r['distance']if n=='distance'else r['NN'][n]
 for n in names:
  pg={g:dict(rows=count[(split,g)],rootmeanMSE=math.fsum((pred(r,n)-r['rootmean'])**2 for r in rr if r['group']==g)/count[(split,g)])for ss,g in count if ss==split};gameout[split][n]=pg
  metrics[n]={'rootmean_gameMSE':mean(lambda r:(pred(r,n)-r['rootmean'])**2),'rootmean_rowMSE':math.fsum((pred(r,n)-r['rootmean'])**2 for r in rr)/len(rr),'z_gameMSE':mean(lambda r:(pred(r,n)-r['z'])**2),'z_rowMSE':math.fsum((pred(r,n)-r['z'])**2 for r in rr)/len(rr),'sign_game':mean(lambda r:float(pred(r,n)*r['z']>0)),'sign_row':sum(pred(r,n)*r['z']>0 for r in rr)/len(rr),'saturation_game':mean(lambda r:float(abs(pred(r,n))>=1)),'saturation_row':sum(abs(pred(r,n))>=1 for r in rr)/len(rr)}
  if n!='distance':
   efn=lambda r:r['rootmean']-r['distance'];rfn=lambda r:pred(r,n)-r['distance'];disp=mean(lambda r:rfn(r)**2);cross=mean(lambda r:efn(r)*rfn(r));gap=metrics[n]['rootmean_gameMSE']-metrics['distance']['rootmean_gameMSE'];assert abs(gap-disp+2*cross)<1e-12;metrics[n].update(gap_to_D=gap,displacement=disp,cross=cross,gain_games=sum(pg[g]['rootmeanMSE']<gameout[split]['distance'][g]['rootmeanMSE']for g in pg))
 for n in names[1:]:
  o=owner['splits'][split][n];assert abs(metrics[n]['rootmean_gameMSE']-o['NN_gameMSE'])<1e-12 and abs(metrics[n]['gap_to_D']-o['delta_NN_minus_D'])<1e-12 and abs(metrics[n]['z_gameMSE']-o['NN_z_MSE_gameweighted'])<1e-12
 for n,key in [('ridge','ridge_unclipped'),('distance_recalibration','distance_reference_unclipped')]:metrics[n]['unclipped_gameMSE']=mean(lambda r:(r[key]-r['rootmean'])**2)
 out['splits'][split]=metrics;out['bins'][split]={}
 for dim,values in [('phase',['early','middle','late']),('cohort',['opening-'+str(v)for v in [8,12,16,20,24,28]]),('difference_bin',range(5))]:
  parts={}
  for v in values:
   b=[r for r in rr if r[dim]==v];part={'rows':len(b),'games':len({r['group']for r in b}),'mass':math.fsum(weight(r)for r in b),'signed_gap':{n:math.fsum(weight(r)*((pred(r,n)-r['distance'])**2-2*(r['rootmean']-r['distance'])*(pred(r,n)-r['distance']))for r in b)for n in names[1:]}};parts[str(v)]=part
  assert abs(math.fsum(p['mass']for p in parts.values())-1)<1e-12
  for n in names[1:]:assert abs(math.fsum(p['signed_gap'][n]for p in parts.values())-metrics[n]['gap_to_D'])<1e-12
  out['bins'][split][dim]=parts
assert stop['samples_added']==5901 and stop['total_samples']==29505<=reg['NNcap'] and proc['exit']==0 and proc['child_waited']and not proc['remaining']
assert J(S/'result.json')['samepass_original_prediction_maxabs']==0
for p in [S/'preregister.json',S/'preregister-amendment-v2.json',S/'coefficients.json',S/'distance-reference-coefficients.json',S/'hidden_features.npz',S/'comparison-per-row.jsonl.gz',S/'result.json',S/'comparison-summary.json',S/'science-stop.json',S/'jobs/hidden-ridge-r1/process.json',Path('tools/ai-sigma-fit-gap-analysis/residual-head-control/forward_fit.py'),Path('tools/ai-sigma-fit-gap-analysis/residual-head-control/distance_reference.py')]:out['inputSHA'][str(p)]=sha(p)
for p,h in out['inputSHA'].items():assert sha(p)==h
with gzip.open(D/'phase2-per-game.json.gz','wt')as f:json.dump(gameout,f,separators=(',',':'))
out.update(phase1_unchanged=True,NN_added=0,newtest=0,static_total_charge=180,cap=180,remaining=0,wall_seconds=time.monotonic()-start,peakRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,ownPID=os.getpid(),own_starttick=Path('/proc/self/stat').read_text().split(') ',1)[1].split()[19],UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),samepass_parity_owner_receipt_only=True,reference_prereg_after_main_job=True,owner_nonreading_assertion_independently_proven=False)
assert out['wall_seconds']<55 and out['peakRSS_bytes']<448*1024**2
(D/'phase2-result.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({'splits':out['splits'],'fit_max':coefdiff,'prediction_max':maxhidden,'wall':out['wall_seconds'],'peak':out['peakRSS_bytes']}))
