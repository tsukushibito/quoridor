import json,pathlib,hashlib,math,statistics,sys,datetime
ROOT=pathlib.Path(__file__).resolve().parents[2]; O=ROOT/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-CLOCK-INDEPENDENT'
name=sys.argv[1] if len(sys.argv)>1 else 'saved97'
p=O/('upstream-needed/clock-factor-primary-r1/turns.jsonl' if name=='saved97' else 'critic100-primary-r1/turns.jsonl')
rows=[json.loads(l) for l in p.read_text().splitlines()];details=[]
for r in rows:
 i=r['identity'];t=i['t0_ms']; c=r['worker_clock']; a=r['owned_ACK'];s=a['at_ms'];lo=s-c['hi_ms'];hi=s-c['lo_ms']; pub=r['response']; n=r['NN'];api=r['API'];assert len(api)==n
 assert all(a.get(k)==0 for k in ['handles','activeNN','live_searches']) and a['active'] is False
 assert pub['late'] is False and pub['fallback']==0 and pub['checkpoint'] is True and pub['stamp_ms']<i['deadline_ms'];assert pub['action'] is not None
 assert abs((pub['stamp_ms']-t)-r['public_elapsed_ms'])<1e-7
 assert abs((s-c['lo_ms'])-r['Worker_stop_interval']['late_ms'])<1e-6
 assert abs((s-c['hi_ms'])-r['Worker_stop_interval']['early_ms'])<1e-6
 assert r['oldACK_before_t0']; assert i['deadline_ms']-t==500 and i['commit_cutoff_ms']-t==402 and i['seal_ms']-t==411
 aftercut=sum(v['awaiter_start_ms']>=i['commit_cutoff_ms']+c['lo_ms'] for v in api)
 afterpub=sum(v['session_run_start_ms']-c['hi_ms']>pub['stamp_ms'] for v in api)
 assert aftercut==r['NN_start_after_cutoff_worker'] and afterpub==r['post_public_NN_start_definite']
 d={'index':r['index'],'engine':r['engine'],'condition':r['condition'],'fixture':r['fixture_id'],'sample':r['sample'],'rep':r['rep'],'public':pub['stamp_ms']-t,'ACK':r['ACK_stamp_ms']-t,'Worker_stop_upper':hi-t,'Worker_stop_lower':lo-t,'transport':[r['stop_node_received_ms']-hi,r['stop_node_received_ms']-lo],'awaiter_aftercutoff':aftercut,'API_afterpublic':afterpub,'NN':n,'completed_simulations':pub['completed_simulations']};details.append(d)
def stats(xs):
 return {'n':len(xs),'median':statistics.median(xs),'p95':sorted(xs)[math.ceil(.95*len(xs))-1],'max':max(xs)} if xs else {'n':0}
groups={}
for e in ['candidate','reference']:
 for c in ['baseline','cooperative']:
  for sm in ['all','steady']:
   rs=[r for r in details if r['engine']==e and r['condition']==c and (sm=='all' or r['sample']=='steady')];groups[f'{e}/{c}/{sm}']={'public':stats([r['public'] for r in rs]),'ACK':stats([r['ACK'] for r in rs]),'Worker_stop_upper':stats([r['Worker_stop_upper'] for r in rs]),'NN':sum(r['NN'] for r in rs),'aftercutoff':sum(r['awaiter_aftercutoff'] for r in rs),'afterpublic':sum(r['API_afterpublic'] for r in rs)}
pairs=[]
for e in ['candidate','reference']:
 for f in set(r['fixture'] for r in details):
  for rep in sorted(set(r['rep'] for r in details if r['sample']=='steady')):
   q=[r for r in details if r['engine']==e and r['fixture']==f and r['rep']==rep and r['sample']=='steady'];
   if len(q)==2:
    b=next(r for r in q if r['condition']=='baseline');c=next(r for r in q if r['condition']=='cooperative');pairs.append({'engine':e,'fixture':f,'rep':rep,'cooperative_minus_baseline_ACK':c['ACK']-b['ACK'],'cooperative_minus_baseline_public':c['public']-b['public'],'NN_difference':c['NN']-b['NN']})
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'input':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'n':len(rows),'NN':sum(r['NN'] for r in details),'all_public_legal_deadline':True,'Worker_stop_upper_le500':sum(r['Worker_stop_upper']<=500 for r in details),'ACK_over500':sum(r['ACK']>500 for r in details),'groups':groups,'paired_steady':pairs,'details':details,'no_tail_or_strength_claim':True}
(O/(name+'-independent-arithmetic.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['n','NN','Worker_stop_upper_le500','ACK_over500','groups','paired_steady']}))
