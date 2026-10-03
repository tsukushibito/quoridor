import pathlib,json,hashlib,subprocess,datetime,time,os,resource,collections
from fractions import Fraction as F
os.sched_setaffinity(0,{0}); begin=time.monotonic(); assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-03T08:02:00+00:00')
D=pathlib.Path(__file__).parent; A=pathlib.Path('research-data/ai-sigma/173-native-ni-arena'); R=pathlib.Path('.artifacts/ai-sigma/resume-20261003/NATIVE-NI-ARENA/runs/native173-quality-e2-r1'); bindings=[]
def read(p):
 b=p.read_bytes();bindings.append({'path':str(p),'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()});return json.loads(b)
def rows(p):
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for line in f:
   h.update(line);n+=1;yield json.loads(line)
 bindings.append({'path':str(p),'rows':n,'SHA256':h.hexdigest(),'bytes':p.stat().st_size})
pre=read(A/'preregister-e2.json'); original=subprocess.check_output(['git','show','8e14cf496047f3c2f19a5824abd219c82ce3b54f:research-data/ai-sigma/173-native-ni-arena/preregister-e2.json']);assert json.loads(original)==pre
assert pre['statistics']['lambda_plus']==[.25,.5,1,1.5,2] and pre['statistics']['lambda_minus']==[.25,.5,1,1.5] and pre['statistics']['theta']==.45 and pre['statistics']['threshold']==20
assert pre['mode']['cores']==[2,4,6] and pre['capacity']['blocks']==200
stop=read(A/'science-stop-e2.json');old=read(A/'epoch1-qualification.json');assert old['registered_games']==6 and old['quality_inference_low']==[0]*6 and old['quality_inference_high']==[1]*6
games={}; prefix=[]; ps=[1]*5;qs=[1]*4;den=1;W=L=draw=unknown=0;firstplus=firstminus=None;counts=collections.Counter();sumlo=sumhi=F(0);total_block_seconds=0
for b in rows(R/'blocks.jsonl'):
 n=b['block'];assert n==len(prefix)+1; vals=[];cores=[];pairs=[]
 for arena in b['results']:
  core=arena['core'];cores.append(core); assert len(arena['games'])==2
  pair=arena['games'];assert {g['candidate_player'] for g in pair}=={1,2};assert len({g['pair'] for g in pair})==1;pairs.append(pair[0]['pair'])
  for g in pair:
   assert g['block']==n and g['core']==core and g['game_id'] not in games;games[g['game_id']]=g;counts[g['status']]+=1;q=g['quality_score']
   if q is None:unknown+=1;vals.append((F(0),F(1)))
   else:
    assert q in [0,.5,1];assert g['status']=='GOAL';assert q==int(g['winner']==g['candidate_player']); vals.append((F(str(q)),F(str(q)))); W+=q==1;L+=q==0;draw+=q==.5
    pawn=g['final_key'].split('|')[g['winner']-1].split(',');assert int(pawn[1])==(8 if g['winner']==1 else 0)
 assert sorted(cores)==[2,4,6] and sorted(pairs)==list(range((n-1)*3+1,n*3+1))
 lo=sum(x[0] for x in vals)/6;hi=sum(x[1] for x in vals)/6; kl=lo*12;kh=hi*12;assert kl.denominator==kh.denominator==1
 for i,a in enumerate([1,2,4,6,8]):ps[i]*=240+a*(5*int(kl)-27)
 for i,a in enumerate([1,2,4,6]):qs[i]*=240-a*(5*int(kh)-27)
 den*=240;plus=F(sum(ps),5*den);minus=F(sum(qs),4*den)
 if plus>=20 and firstplus is None:firstplus=n
 if minus>=20 and firstminus is None:firstminus=n
 prefix.append({'block':n,'Ylow':str(lo),'Yhigh':str(hi),'NI_numerator':str(sum(ps)),'NI_denominator':str(5*den),'inferiority_numerator':str(sum(qs)),'inferiority_denominator':str(4*den),'NI':plus>=20,'inferiority':minus>=20});sumlo+=lo;sumhi+=hi;total_block_seconds+=b['elapsed_ms']/1000
assert len(prefix)==33 and len(games)==198
owner=read(A/'epoch2-inference.json')
for x,y in zip(prefix,owner['rows']):
 assert x['block']==y['block'] and F(x['NI_numerator'],) / int(x['NI_denominator'])==F(int(y['plus_numerator']),int(y['plus_denominator']))
 assert F(int(x['inferiority_numerator']),int(x['inferiority_denominator']))==F(int(y['minus_numerator']),int(y['minus_denominator']))
assert len(owner['rows'])==33
admissions=list(rows(R/'block-admissions.jsonl'));starts=list(rows(R/'block-starts.jsonl'));assert len(admissions)==len(starts)==33
for i,(a,s) in enumerate(zip(admissions,starts),1):
 assert a['decision']=='launch_allowed' and s['block']==i and len(s['planned'])==6
 assert datetime.datetime.fromisoformat(a['UTC'])<=datetime.datetime.fromisoformat(s['UTC'].replace('Z','+00:00'))
clock_errors=[];maxima={};sums=collections.Counter();journalcounts=collections.Counter();corecounts={};lastrows={};firstrows={}
fields=['firstCP_ms','public_actual_ms','cut_actual_ms','cleanup_after_public_ms','API_total_ms','pipe_total_ms','common_legal_preparation_ms','previous_zero_to_t0_ms']
for core in [2,4,6]:
 previous=None;count=0
 for x in rows(R/f'core{core}/journal.jsonl'):
  count+=1;gid=x['game_id'];g=games[gid];assert g['core']==core and x['block']==g['block'] and x['pair']==g['pair'];journalcounts[gid]+=1;lastrows[gid]=x;firstrows.setdefault(gid,x)
  cp=x['public_cp'];reasons=[]
  if cp is None:reasons.append('NO_PUBLIC_CP')
  else:
   if cp['generation']!=x['generation']:reasons.append('GENERATION')
   if not(0<=cp['receive_ms']<=cp['admit_ms']<=402):reasons.append('ADMIT402')
   for k in ['receive_ms','admit_ms']:
    if k not in maxima or cp[k]>maxima[k]['value']:maxima[k]={'value':cp[k],'game':gid,'generation':x['generation'],'core':core}
  if x['public_actual_ms']>500:reasons.append('PUBLIC500')
  if x['NN_calls']!=x['NN_returned']:reasons.append('NN_UNRETURNED')
  if x['zero']!={'activeNN':0,'handles':0,'active':False}:reasons.append('NONZERO')
  if previous is not None:
   gap=x['controller_t0_ms']-(previous['controller_t0_ms']+previous['quiescent_gate_observed_ms'])
   if gap<0:reasons.append('NEXT_BEFORE_ZERO')
   if abs(gap-x['previous_zero_to_t0_ms'])>1e-5:reasons.append('NEXT_GAP_DISAGREES')
  if x['error'] is not None or x['status']!='COMPLETE':reasons.append('REQUEST_ERROR')
  if reasons:clock_errors.append({'game':gid,'generation':x['generation'],'core':core,'reasons':reasons})
  for k in fields:
   v=x.get(k)
   if v is not None:
    sums[k]+=v
    if k not in maxima or v>maxima[k]['value']:maxima[k]={'value':v,'game':gid,'generation':x['generation'],'core':core}
  for k in ['NN_calls','NN_returned','NN_discarded','terminal_noNN','CP_received','CP_admitted','CP_late_discarded','CP_schema_rejected']:sums[k]+=x[k]
  previous=x
 corecounts[str(core)]=count
for gid,g in games.items():
 assert journalcounts[gid]==g['plies_played']==g['requests']; assert lastrows[gid]['player']==g['winner'];assert lastrows[gid]['ply']+1==g['final_ply'];assert firstrows[gid]['ply']+g['plies_played']==g['final_ply']
assert sum(journalcounts.values())==8268 and sums['NN_calls']==sums['NN_returned']==537460
result=read(R/'result.json');assert result['blocks_completed']==33 and result['stop']==stop['stop']=='SCIENCE_DEADLINE_HEADROOM' and result['primary'] is None and result['startup_NN']==6
headroom=(datetime.datetime.fromisoformat(pre['limits']['science_end'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(stop['end_UTC'])).total_seconds();assert headroom<305
assert not stop['remaining'] and not stop['unknown_owned'];assert stop['monitor_stop']['state']=='READY' and stop['monitor_stop']['failure'] is None
for c in stop['inner_close']:
 assert c['exit']['code']==0 and c['usedNN']==sum(v['receipt']['NN_total'] for v in c['closed'].values())
 for v in c['closed'].values():assert v['exit']['code']==0 and all(e['code']==0 for e in v['receipt']['exit'])
freeze={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in pre['freeze'].items()};assert all(freeze.values())
prior_scopes=['158-formal-ni-plan','161-formal-clock','166-native-comparison-scope','168-native-stageA-independent','169-native-games-independent','172-native-ni-efficient']
allocated=sum(p.stat().st_blocks*512 for n in prior_scopes for p in (pathlib.Path('research-data/ai-sigma')/n).rglob('*') if p.is_file())
storage={'old_unknown_conservative':88190086,'prior_data_allocated':allocated,'new_scope_metadata_forecast':2097152,'conservative_total':88190086+allocated+2097152,'guard':117440512,'unknown_decrement':0,'parent_extra_reservation':0};assert storage['conservative_total']<storage['guard']
output={'issue':'quoridor-4lc.175','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'registered_blocks':33,'registered_pairs':99,'registered_games':198,'W':W,'D':draw,'L':L,'unknown':unknown,'quality_mean_interval':[str(sumlo/33),str(sumhi/33)],'future_unregistered_games':1002,'capacity_interval':[str(sumlo/200),str((sumhi+167)/200)],'NI_final':str(plus),'inferiority_final':str(minus),'NI_float':float(plus),'inferiority_float':float(minus),'first_NI':firstplus,'first_inferiority':firstminus,'prefix':prefix,'journal_public':sum(journalcounts.values()),'clock_errors':clock_errors,'maxima':maxima,'sums':dict(sums),'percore_public':corecounts,'headroom_seconds_at_outerend':headroom,'job_wall_seconds':(datetime.datetime.fromisoformat(stop['end_UTC'])-datetime.datetime.fromisoformat(stop['start_UTC'])).total_seconds(),'sum_block_seconds':total_block_seconds,'startup_NN_separate':6,'old_epoch_quality_unknown':6,'old_epoch_wealth_separate':True,'freeze_matches':freeze,'bindings':bindings,'storage':storage,'elapsed_seconds':time.monotonic()-begin,'RSS_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid(),'CPU':[0],'new_NN':0,'new_game':0,'conditional_mean_proved':False,'kernel_CPU_exact':False,'all_host_guarantee':False,'deep_RuleA_replay_performed':False,'verdict':'UNCERTAIN supported' if firstplus is None and firstminus is None and not clock_errors else 'NEEDS_CLASSIFICATION'}
(D/'check-result.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({k:v for k,v in output.items() if k not in ['bindings','prefix','freeze_matches']}))
