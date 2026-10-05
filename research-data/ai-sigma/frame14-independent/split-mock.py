"""NN0 specification witnesses, separate from the owner exporter/trainer."""
import json,hashlib,struct,copy,time,os,resource,datetime,pathlib
os.sched_setaffinity(0,{0});start=time.monotonic();D=pathlib.Path('research-data/ai-sigma/frame14-independent')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def input_signature(r):
 p=r['side']-1
 return digest(['QF1-net-input-f32-v1',sorted(r['ids'][p]),sorted(r['ids'][1-p]),[struct.pack('<f',v).hex()for v in r['distance']]])
def raw_signature(r):return digest([sorted(r['ids'][0]),sorted(r['ids'][1]),r['distance'],r['side']])
def keys(r):return r['state'],r['history'],input_signature(r)
def signatures(rows):return [set(k[i]for k in map(keys,rows))for i in range(3)]
def mask(rows,seen):return {r['id']:not any(k in s for k,s in zip(keys(r),seen))for r in rows}
def row(rid,game,side,ids,state,history,distance):return dict(id=rid,game=game,side=side,ids=ids,state=state,history=history,distance=distance)
a=row('train','T',1,[[4,82,290,301],[5,83,290,301]],'S1','H1',[.1,.2])
b=row('same-net-other-state','V1',2,list(reversed(a['ids'])),'S2','H2',[.1,.2])
c=row('state-only','V2',1,[[6,84,290,301],[7,85,290,301]],'S1','H3',[.3,.4])
e=row('history-only','V3',1,[[8,86,290,301],[9,87,290,301]],'S4','H1',[.5,.6])
f=row('unexposed','V3',1,[[10,88,290,301],[11,89,290,301]],'S5','H5',[.7,.8])
assert raw_signature(a)!=raw_signature(b) and input_signature(a)==input_signature(b)
seen=signatures([a]);m=mask([b,c,e,f],seen);assert m=={b['id']:False,c['id']:False,e['id']:False,f['id']:True}
changed=[dict(r,rootmean=999,z=-999,loss=1000)for r in [b,c,e,f]];assert m==mask(changed,seen),'label-free rule'
g=copy.deepcopy(a);g['distance'][0]+=.00000000001;assert raw_signature(g)!=raw_signature(a) and input_signature(g)==input_signature(a),'float32 alias witness'
# A larger training union fixes one validation mask for every smaller nested stage.
t2=copy.deepcopy(f);t2['id']='train96-extra';t2['game']='T96';maxseen=signatures([a,t2]);fixed=mask([b,c,e,f],maxseen)
assert fixed=={r['id']:False for r in [b,c,e,f]}
assert mask([b,c,e,f],seen)!=fixed,'per-stage mask would silently change evaluation set'
allgames=['V1','V2','V3'];eligible={g:sum(m[r['id']]for r in [b,c,e,f]if r['game']==g)for g in allgames};assert eligible=={'V1':0,'V2':0,'V3':1}
errors={f['id']:2.0};means=[sum(errors[r['id']]for r in [b,c,e,f]if r['game']==g and m[r['id']])/n for g,n in eligible.items()if n]
assert len(means)==1 and sum(means)/len(means)==2 and sum(means)/len(allgames)!=2,'zero eligibility is not zero loss'
# Family duplication is a split error even if its rows have disjoint states.
families={'train':{'F1'},'validation':{'F2'},'test':{'F3'}};assert not (families['train']&families['validation']);families['test'].add('F1');assert families['train']&families['test']
# Mock sealing proves only dependency ordering; it is not an actual dataset access audit.
events=['label_free_mask_fixed','validation_read','candidate_weight_settings_frozen','test_labels_opened_once'];assert events.index('candidate_weight_settings_frozen')<events.index('test_labels_opened_once')
out={'issue':'quoridor-4lc.196','supported_smallmock':True,'witnesses':['raw-side signature misses equivalent STM-network input','float64 JSON differs but float32 input equals','state/history/QF1 OR; conjunction would miss exposure','targets/loss not used in mask','maxtrain96 fixed mask differs from stage-specific masks','zero eligible games kept as denominator status, not zero loss','family partition disjointness','mock freeze precedes once-only test-label access'],'conditional_game_equal_target':{'all_games':3,'positive_eligible_games':1,'eligible_counts':eligible,'positive_game_mean':2.0},'actual_test_targets_read':False,'actual_model_forward':0,'actual_dataset_sealing_certified':False,'wall_s':time.monotonic()-start,'RSS_B':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid(),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
D.joinpath('split-mock.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
