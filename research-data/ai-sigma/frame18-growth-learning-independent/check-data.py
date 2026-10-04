"""229 label-free generation/split/exposure arithmetic. Stdlib only; no labels."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,math,os,resource,struct,time
os.sched_setaffinity(0,{0});resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2)); t=time.monotonic()
D=Path('research-data/ai-sigma/frame18-growth-learning-independent');P=Path('research-data/ai-sigma/frame18-data-learning');A=P/'dataset-v1/adapter'; hashes={}
def read(p):
 p=Path(p);b=p.read_bytes();hashes[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def rows(p):
 p=Path(p);hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 with gzip.open(p,'rt') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def require(v,message):
 if not v:raise ValueError(message)
stop=read(P/'generation-final-stop-compact.json');require(stop['gen_stop'] and stop['sourcewriter_stop'] and not stop['current_exact_children'],'owner generation stop')
plan=read(P/'dataset-v1/plan.json');quantity=read(P/'dataset-v1/quantity-freeze.json');prep=read(A/'preparation-receipt.json');mask=read(A/'fixed-maximum-mask.json');rule=read(P/'learning-plan-v1/before-curves-selection-rule.json')
require(not mask['labels_used'] and not prep['labels_opened'],'label-free boundary'); require(hashes[str(A/'fixed-maximum-mask.json')]==prep['mask_sha256'],'mask binding')
games=plan['games'];bygame={g['game_id']:g for g in games};require(len(games)==len(bygame)==768,'768 planned games');family={g['family']:g for g in games};require(len(family)==768,'family unique');require(games==quantity['all_slots'],'quantity same slots')
partition=collections.Counter(g['split'] for g in games);require(dict(partition)=={'train':576,'validation':96,'test':96},'partition counts');ordered=sorted((g for g in games if g['split']=='train'),key=lambda g:g['train_slot']);require([g['train_slot']for g in ordered]==list(range(1,577)),'nested train slots')
originals={};inputcounts={}
for p,expected in prep['input_bindings'].items():
 n=0
 for r in rows(p):
  require(not {'rootmean','z','rootNN','winner','value','target','pi','policy','prediction','loss'}.intersection(r),'metadata contains labels')
  require(r['id'] not in originals,'duplicate metadata input');g=bygame[r['game_id']];require(r['group']==g['family'] and r['split']==g.get('source_split',g['split']),'input family/source split')
  originals[r['id']]=dict(r,split=g['split'],cohort=g['cohort'],**({'source_split':r['split']}if r['split']!=g['split']else{}),**({'train_slot':g['train_slot']}if g['split']=='train'else{}));n+=1
 require(hashes[p]==expected,'input SHA '+p);inputcounts[p]=n
metadata=list(rows(A/'canonical.jsonl.gz'));require(hashes[str(A/'canonical.jsonl.gz')]==prep['metadata_sha256'],'canonical SHA');require(len(metadata)==len(originals)==37123,'metadata row total')
counts=collections.Counter();trainsets=[set(),set(),set()];valsets=[set(),set(),set()];ids=set()
def sig(r):
 require(r['side']in(1,2) and len(r['ids'])==len(r['distance'])==2,'side/shape')
 v=r['side']-1;bits=tuple(struct.unpack('<I',struct.pack('<f',x))[0]for x in r['distance']);q=('QF1-f32-STM-v1',tuple(sorted(r['ids'][v])),tuple(sorted(r['ids'][1-v])),bits)
 return r['state_key'],r['history_key'],q
for r in metadata:
 require(r==originals[r['id']],'canonical independent alias mapping');require(r['id']not in ids,'row ID repeat');ids.add(r['id']);counts[r['game_id']]+=1
 if r['split']in('train','validation'):
  out=trainsets if r['split']=='train'else valsets
  for i,s in enumerate(sig(r)):out[i].add(s)
require(set(mask['rows'])==ids,'mask all rows')
exposure=collections.Counter();eligible=collections.Counter();groupeligible=collections.Counter();groupmask={}
for r in metadata:
 shared=[]
 if r['split']!='train':
  for i,s in enumerate(sig(r)):
   if s in trainsets[i] or (r['split']=='test' and s in valsets[i]):shared.append(['state','history','QF1'][i])
 m=mask['rows'][r['id']];require(m=={'primary_eligible':not shared,'exposure':sorted(shared),'split':r['split'],'group':r['group']},'OR mask differs '+r['id'])
 exposure[r['split']]+=bool(shared);eligible[r['split']]+=not shared;groupeligible[r['group']]+=not shared
for g in games:require(counts[g['game_id']]==g['expected_rows'],'pergame rows');require(groupeligible[g['family']]>0,'zero eligible game')
require(not mask['zero_eligible_games'],'zero-eligible list');require(sum(n for gid,n in counts.items() if bygame[gid].get('source_split')!='evaluation')==stop['counts']['Rjoint']==32520,'new rows32520');require(sum(g.get('source_split')=='evaluation' for g in games)==96,'old96 alias only')
stages={}
for n in [192,576]:
 descriptor=read(A/f'{n}.stage.json');sampling=read(A/f'{n}-sampling.json');chosen={g['family']for g in ordered[:n]}; require(set(descriptor['train_groups'])==chosen==set(sampling['train_groups']),'stage nested groups')
 rr=[r for r in metadata if r['split']=='train'and r['group']in chosen];c=collections.Counter(r['group']for r in rr);require(len(c)==n,'positive stage G');require(set(sampling['row_sampling_weights'])=={r['id']for r in rr},'sampling rows');mass=collections.defaultdict(float)
 for r in rr:
  w=1/(n*c[r['group']]);require(abs(w-sampling['row_sampling_weights'][r['id']])<1e-15,'gameequal weight');mass[r['group']]+=w
 require(all(abs(v-1/n)<1e-12 for v in mass.values()),'game mass');require(sampling['train_rows']==len(rr),'stage row count');require(descriptor['mask_sha256']==prep['mask_sha256'] and descriptor['metadata_sha256']==prep['metadata_sha256'],'same maximum mask')
 cfg=read(P/f'learning-plan-v1/config-{n}.json');settings=read(P/f'learning-plan-v1/settings-{n}.json');tr=cfg['training'];require(tr['steps']==2000 and tr['batch_size']==128 and tr['seed']==19080311 and tr['target']=='rootmean'and tr['sampling']=='game','fixed same compute'); require(cfg['optimizer']['lr']==.0001 and cfg['optimizer']['weight_decay']==0,'LR/WD'); scale=Path('research-data/ai-sigma/frame15-input-scale-control/scale.json').resolve();require(settings['sources'][str(scale)]==hashlib.sha256(scale.read_bytes()).hexdigest(),'oldscale binding')
 stages[n]={'positive_games':n,'rows':len(rr),'cohorts':dict(collections.Counter(g['cohort']for g in ordered[:n])),'training_samples':256000,'expected_samples_per_game':256000/n,'samples_over_rows':256000/len(rr),'oldscale_SHA':settings['sources'][str(scale)],'seed':tr['seed'],'actual_initial_tensor_or_function_receipt':'pending; config equality alone is not reauthentication'}
sec=quantity['secondary_nonselection'];points=rule['fixed_points'];chosen=min(points,key=lambda s:(abs(s/576-400/192),s));require(chosen==sec['large_step']==1200 and sec['small_step']==400 and rule['secondary_nonselection']==sec,'precurve matched exposure');require(sec['distance']==abs(chosen/576-400/192),'secondary distance')
attempts=[]
for p in sorted(list((P/'jobs').glob('*/process.json'))+list((P/'test-sealed/jobs').glob('*/process.json'))):
 x=read(p);require(x['all_child_waited']and x['current_exact_absent']and not x['remaining'],'allattempt process stop');pp=Path('/proc',str(x['runner_pid']),'stat')
 if pp.exists():require(pp.read_text().rsplit(')',1)[1].split()[19]!=str(x['runner_tick']),'fresh exactrunner')
 attempts.append({'run':x['run'],'NN':x['sample_equivalent'],'wall':x['jobwall_seconds'],'exit':x['exit'],'reason':x['stop_reason']})
require(all(a['NN']is not None for a in attempts),'physical NN unknown remains');wall=sum(a['wall']for a in attempts);nn=sum(a['NN']for a in attempts);require(abs(wall-stop['guardian_allattempt_wall_s'])<1e-6 and nn==stop['physicalNN_allattempt'],'cost sum');require(nn<2200000 and wall<5400,'gen caps')
for p,h in hashes.items(): require(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,'immutable inputs '+p)
out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PASS':True,'new_games':672,'all_planned_with_alias':768,'partition':dict(partition),'rows':len(metadata),'new_rows':32520,'alias_rows':4603,'row_partition':dict(collections.Counter(r['split']for r in metadata)),'exposed_rows':dict(exposure),'eligible_rows':dict(eligible),'zeroeligible_games':0,'stages':stages,'secondary':sec,'attempts':attempts,'physicalNN_allattempt':nn,'guardian_allattempt':wall,'inputSHA':hashes,'wall':time.monotonic()-t,'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'limits':['metadata independent signatures; opaque history/state and sharedRuleA teacher qualification are producer references','no sealed labels/oldtest/formal173 read','samecompute differs expected exposures, old96 alias/distribution/oldscale not purequantity','initialfunction same seed is provisional pending savedparity; no model import'],'newNN':0}
(D/'data-result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['PASS','rows','exposed_rows','stages','physicalNN_allattempt','guardian_allattempt','wall','peakRSS']}))
