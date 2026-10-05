"""Independent saved-output arithmetic; standard library, no owner evaluator imports."""
import collections, datetime, gzip, hashlib, json, math, os, pathlib, random, resource, time, zipfile
os.sched_setaffinity(0, {0})
start=time.monotonic()
D=pathlib.Path('research-data/ai-sigma/frame14-independent')
L=pathlib.Path('research-data/ai-sigma/frame14-learning')
A=pathlib.Path('research-data/ai-sigma/frame14-teachers/final-qf1-v2')
reads={}
def blob(p):
    p=pathlib.Path(p); b=p.read_bytes(); reads[str(p)]=hashlib.sha256(b).hexdigest(); return b
def js(p): return json.loads(blob(p))
def rows(p): return [json.loads(s) for s in gzip.decompress(blob(p)).splitlines()]
def close(a,b): assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(a,b)
def mean(xs): return math.fsum(xs)/len(xs)
def grouped(rs, fn):
    out=collections.defaultdict(list)
    for r in rs: out[r['game']].append(fn(r))
    return {g:mean(v) for g,v in out.items()}
f=js(L/'test-freeze-v2.json'); c=js(L/'candidate-freeze.json'); sel=js(L/'selection.json')
reason=js(L/'test-freeze-v2-reason.json'); prereg=js(L/'quantity-preregister.json')
res=js(L/'test-r1/result.json'); begun=js(L/'test-r1/started.json'); proc=js(L/'jobs/sealed-test-r1/process.json')
assert reads[str(L/'test-freeze-v2.json')]=='45c27fbf896f7c205b393253fa89a39736fe5ef1805c4c9f7c9dfafd463dd84d'
assert f['candidate_freeze_sha256']==reads[str(L/'candidate-freeze.json')]
assert res['freeze_sha256']==begun['freeze_sha256']==reads[str(L/'test-freeze-v2.json')]
for name,h in f['source_sha256'].items(): assert hashlib.sha256(blob(pathlib.Path('tools/nnue-training')/name)).hexdigest()==h
assert sel['candidate_stage']==48 and sel['best_step']==c['best_step']==0
assert datetime.datetime.fromisoformat(prereg['UTC'])<datetime.datetime.fromisoformat(sel['UTC'])<datetime.datetime.fromisoformat(reason['UTC'])
assert datetime.datetime.fromisoformat(reason['UTC'])<datetime.datetime.fromisoformat(proc['UTC'])-datetime.timedelta(seconds=proc['wall_seconds'])
assert proc['exit']==0 and proc['child_waited'] and proc['remaining']==[] and proc['current_exact_identity_absent']
try:
    stat=pathlib.Path('/proc')/str(proc['identity']['pid'])/'stat'
    assert stat.read_text().split(') ',1)[1].split()[19]!=proc['identity']['tick']
except FileNotFoundError: pass
meta=rows(A/'all144-metadata.jsonl.gz'); byid={r['id']:r for r in meta}; mask=js(A/'fixed-exposure-mask.json')
labs=rows(A/'training-labels.jsonl.gz'); assert len(labs)==5901
assert {r['id'] for r in labs}=={r['id'] for r in meta if r['split'] in ('train','validation')}
z_p1=collections.defaultdict(set)
for r in labs:
    m=byid[r['id']]; assert r['split']==m['split'] and -1<=r['rootmean']<=1 and r['z'] in (-1,1)
    z_p1[m['group']].add(r['z']*(1 if m['side']==1 else -1))
assert all(len(v)==1 for v in z_p1.values())
stages={}; initial_hashes=[]
for n in (24,48,96):
    run=L/'runs'/f'frame14-train{n}-r1'
    s=js(run/'summary.json'); cfg=js(run/'config.json'); data=js(run/'dataset.json')
    hist=[json.loads(x) for x in blob(run/'history.jsonl').splitlines()]
    assert [x['step'] for x in hist]==list(range(0,2001,100))
    assert s['step']==2000 and s['best_step']==0 and s['status']=='max_steps' and not s['test_evaluated']
    assert cfg['training']['target']=='rootmean' and cfg['training']['batch_size']==128 and cfg['training']['steps']==2000
    assert cfg['training']['seed']==19080311 and cfg['evaluation']['monitor']=='game'
    assert all(x['train_samples_seen']==x['step']*128 for x in hist)
    for x in hist:
        for split,key in [('train','train_games'),('validation','validation_games')]:
            games=x[key]; assert len(games)==(n if split=='train' else 24)
            for target in ('rootmean','z'):
                close(mean([g[target+'_game_equal_mse'] for g in games.values()]),x[split][target+'_game_equal_mse'])
                close(sum(g[target+'_mse']*g[target+'_rows'] for g in games.values())/sum(g[target+'_rows'] for g in games.values()),x[split][target+'_mse'])
        assert x['validation_eligible_zero_games']==[]
    close(min(x['validation']['rootmean_game_equal_mse'] for x in hist),s['best_validation_mse'])
    assert hist[-1]==s['last_evaluation']
    ids={r['id'] for r in meta if r['split']=='train' and r['train_slot']<=n}
    train=collections.defaultdict(list)
    for r in labs:
        if r['id'] in ids: train[byid[r['id']]['group']].append(r['rootmean'])
    constant=mean([mean(v) for v in train.values()]); close(constant,data['constant'])
    initial_hashes.append(data['initial_state_sha256'])
    stages[n]={'train_rows':len(ids),'train_samples':hist[-1]['train_samples_seen'],'equivalent_epochs':256000/len(ids),'constant':constant,'initial_validation':hist[0]['validation'],'last_validation':hist[-1]['validation'],'last_train':hist[-1]['train'],'curve_points':len(hist),'saved_elapsed_s':s['elapsed_s']}
assert len(set(initial_hashes))==1 and initial_hashes[0]==f['initial_state_sha256']
close(stages[48]['constant'],f['constant'])
checkpoints={'candidate':(f['checkpoint'],f['checkpoint_sha256']),'initial':(f['initial_checkpoint'],f['initial_checkpoint_sha256'])}
for name,x in f['quantity'].items():
    assert x['step']==2000 and x['train_samples']==256000 and x['initial_state_sha256']==f['initial_state_sha256']
    assert x['config']==f['config']; checkpoints[name]=(x['checkpoint'],x['checkpoint_sha256'])
storage_sha={}
for name,(path,h) in checkpoints.items():
    b=blob(path); assert hashlib.sha256(b).hexdigest()==h
    import io
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        entries=sorted([n for n in z.namelist() if '/data/' in n],key=lambda n:int(n.rsplit('/',1)[1]))
        storage_sha[name]=hashlib.sha256(b''.join(z.read(n) for n in entries)).hexdigest()
assert storage_sha==res['weight_SHA_by_model']
assert storage_sha['candidate']==storage_sha['initial']==f['initial_state_sha256']
assert res['prediction_reused']=={'initial':'candidate'} and res['unique_NN_models']==3 and res['samples']==3285<=4380
rr=rows(L/'test-r1/per-row.jsonl.gz'); assert len(rr)==1095 and len({r['id'] for r in rr})==1095
assert {r['id'] for r in rr}=={r['id'] for r in meta if r['split']=='test'}
for r in rr:
    m=byid[r['id']]; assert r['game']==m['group'] and r['mask']==mask['rows'][r['id']] and r['mask']['primary_eligible']
    assert r['z'] in (-1,1) and -1<=r['rootmean']<=1 and all(math.isfinite(v) and -1<=v<=1 for v in r['values'].values())
    assert r['values']['candidate']==r['values']['initial']
    z_p1[r['game']].add(r['z']*(1 if m['side']==1 else -1))
assert len(z_p1)==144 and all(len(v)==1 for v in z_p1.values())
models={}; losses={}; signs={}
for name in (*rr[0]['values'],'constant'):
    value=lambda r: f['constant'] if name=='constant' else r['values'][name]
    out={'rows':len(rr),'games':len({r['game'] for r in rr})}; losses[name]={}
    for target in ('rootmean','z'):
        fn=lambda r:(value(r)-r[target])**2
        out[target+'_mse']=mean([fn(r) for r in rr]); gl=grouped(rr,fn)
        out[target+'_game_equal_mse']=mean(list(gl.values()));losses[name][target]=gl
    out['z_sign_accuracy']=mean([value(r)*r['z']>0 for r in rr]);out['saturation_fraction']=mean([abs(value(r))>=.9 for r in rr])
    signs[name]=grouped(rr,lambda r:float(value(r)*r['z']>0))
    for k,v in out.items(): close(v,res['models'][name]['primary'][k]);close(v,res['models'][name]['secondary_all'][k])
    for target in ('rootmean','z'):
        for g,v in losses[name][target].items(): close(v,res['models'][name]['games'][g]['primary'][target+'_game_equal_mse'])
    models[name]=out
def bootstrap(a,b):
    gs=sorted(a); assert set(gs)==set(b) and len(gs)==24
    delta={g:a[g]-b[g] for g in gs}; rng=random.Random(19580311)
    bs=sorted(sum(delta[rng.choice(gs)] for _ in gs)/len(gs) for _ in range(2000))
    return {'delta':mean(list(delta.values())),'percentile95':[bs[49],bs[1949]],'groups':24,'seed':19580311,'replicates':2000}
intervals={}
for target in ('rootmean','z'):
    intervals[target]={}
    for key,a,b in [('candidate_minus_initial','candidate','initial'),('candidate_minus_constant','candidate','constant'),('quantity96_minus24','stage96_last','stage24_last')]:
        v=bootstrap(losses[a][target],losses[b][target]); saved=res['paired_intervals'][target][key]
        close(v['delta'],saved['delta'])
        for x,y in zip(v['percentile95'],saved['percentile95']):close(x,y)
        intervals[target][key]=v
v=bootstrap(signs['stage96_last'],signs['stage24_last']);saved=res['paired_intervals']['z_sign_quantity96_minus24']
close(v['delta'],saved['delta'])
for x,y in zip(v['percentile95'],saved['percentile95']):close(x,y)
intervals['z_sign_quantity96_minus24']=v
for path,h in reads.items(): assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==h,('changed',path)
out={'status':'PASS_FINITE_SAVED_ARITHMETIC','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'wall_seconds':time.monotonic()-start,'peak_RSS_B':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'NN_model_forward_GPU_train_game':0,'stages':stages,'storage_weightSHA_independent_zip_bytes':storage_sha,'models':models,'paired_intervals':intervals,'z_STM_game_consistent':144,'readset_SHA256':reads,'teacher_truth_or_forward_recognition':False,'limits':['No model reconstruction/forward; zip storage bytes and saved output arithmetic only','All144 GOAL/teacher pi qualification retain owner/sharedRuleA limits','freeze ordering binds recorded receipts; no allperson nonread or OS isolation guarantee','bootstrap conditional on fixed24games; no strength or unique cause inference']}
(D/'final-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','UTC','pid','wall_seconds','peak_RSS_B']}))
