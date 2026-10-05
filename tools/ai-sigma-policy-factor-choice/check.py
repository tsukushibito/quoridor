import json,pathlib,tarfile,hashlib,math,struct,datetime,os
D=pathlib.Path('research-data/ai-sigma/136-policy-factor-choice');BASE=pathlib.Path('research-data/ai-sigma');refs={}
def raw(task,archive):
 p=BASE/task/archive
 with p.open('rb') as f:refs[str(p)]=hashlib.file_digest(f,'sha256').hexdigest()
 with tarfile.open(p) as t:return json.load(t.extractfile(next(m for m in t if m.name.endswith('browser-result.json'))))
def load(p):
 p=pathlib.Path(p);refs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def tie(a):
 x=1979^a;x=((x^(x>>30))*0xbf58476d1ce4e5b9)&((1<<64)-1);x=((x^(x>>27))*0x94d049bb133111eb)&((1<<64)-1);return x^(x>>31)
def root_summary(cp,kind):
 es=cp['root_edges'];assert es and all(len(e)==4 and e[2]>=0 and math.isfinite(e[1]) and e[1]>=0 and math.isfinite(e[3]) for e in es)
 n=sum(e[2] for e in es);assert n+1==(cp['simulations'] if kind=='candidate' else cp['root_visits'])
 selected=(max(es,key=lambda e:(e[2],e[1],-tie(e[0]))) if kind=='candidate' else max(es,key=lambda e:e[2]))[0];assert selected==cp['action']
 maxv=max(e[2] for e in es);ties=[e for e in es if e[2]==maxv]
 q=lambda e: (e[3]/e[2])*(1 if kind=='candidate' else -1) if e[2] else None
 return {'action':selected,'edge_sum':n,'rootN':n+1,'rootN_basis':'candidate source convention, reference raw root_visits','max_visit':maxv,'max_visit_ties':[{'action':e[0],'prior':e[1],'visits':e[2],'parent_Q':q(e)} for e in ties],'finish_first_same_order':ties[0][0],'visited':sum(e[2]>0 for e in es),'unvisited':sum(e[2]==0 for e in es),'visited_parentQ_negative':sum(e[2]>0 and q(e)<0 for e in es),'legal':len(es),'terminal_value':cp['terminal_value'],'CP_NN':cp['nn_calls'],'parentQ_missing':kind=='candidate','no_parentQ_imputed':True}
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def nextselect(es,C,N):
 rt=f32(math.sqrt(f32(f32(N)+f32(1))));out=[]
 for a,p,n,v in es:
  q=f32(v/n) if n else 0.0
  u=f32(f32(f32(C*p)*rt)/f32(n+1));score=f32(q+u);out.append((score,-tie(a),a))
 best=max(out);return {'action':best[2],'score':best[0],'scorebits':struct.unpack('<I',struct.pack('<f',best[0]))[0],'meaning':'hypothetical next selection using std f32 transcription, not Rust runtime/full search'}
x=raw('132-deep-node-comparison','all-attempts.tar.gz');fixtures=load(BASE/'132-deep-node-comparison/fixed-inputs.json')['fixtures'];ids=[f['id'] for f in fixtures[2:4]]
selected=[r for r in x['deep_results'] if r['spec']['phase']=='primary' and r['fixture_id'] in ids];assert len(selected)==4
roots=[]
for idx,fixture in zip([3,4],ids):
 pair=[r for r in selected if r['fixture_id']==fixture];assert len(pair)==2
 a=next(r for r in pair if r['engine']=='candidate');b=next(r for r in pair if r['engine']=='reference')
 assert a['trace'][0]['key']==b['trace'][0]['key'] and sorted(a['trace'][0]['history'])==sorted(b['trace'][0]['history'])
 assert a['numeric'][0]['features_bits']==b['numeric'][0]['features_bits']
 assert a['numeric'][0]==b['numeric'][0]
 for r in pair:
  z=root_summary(r['cp'],r['engine']);z.update(input_index=idx,engine=r['engine'],backup=r['completed_backups'],NN=r['NN_calls'],terminal_noNN=r['terminal_noNN_backups'],root_turn=r['trace'][0]['turn'])
  assert r['completed_backups']==32 and r['NN_calls']==32 and r['terminal_noNN_backups']==0
  if r['engine']=='candidate':z['nextselect_C1_5']=nextselect(r['cp']['root_edges'],1.5,32);z['nextselect_C1']=nextselect(r['cp']['root_edges'],1.,32)
  roots.append(z)
# Only the preselected third new move roots, not each row's root.
x1=raw('134-local-move-quality','quality134-group1-r3.tar.gz');x2=raw('134-local-move-quality','quality134-group2-r1.tar.gz')
a=next(r for r in x1['rows'] if r['spec'].get('game_id')=='input3-rep1-A' and r['spec']['turn']==2);b=next(r for r in x2['rows'] if r['spec'].get('game_id')=='input3-rep2-A' and r['spec']['turn']==2)
assert all(a['identity'][k]==b['identity'][k] for k in ['key','history','legal_prefix','model','limits'])
assert a['diagnostic']['numeric'][0]==b['diagnostic']['numeric'][0]
progress=[]
for r in [a,b]:
 progress.append({v['completed_backup']:v['action'] for v in r['diagnostic']['sab_publications']})
common=sorted(set(progress[0]) & set(progress[1])); common_progress=[{'completed_backup':k,'rep1_Action':progress[0][k],'rep2_Action':progress[1][k],'same':progress[0][k]==progress[1][k]} for k in common]
rep=[]
for r in [a,b]:
 z=root_summary(r['diagnostic']['validated_cp'],'reference');z.update(game=r['spec']['game_id'],physical_slot=r['spec']['engine'],actual_policy=r['spec']['policy'],sameinput=True,same_root_NN=True,raw_numeric_selected_gate=r['spec']['numeric_selected'],newmove=3);rep.append(z)
x4=raw('134-local-move-quality','quality134-group3-r1.tar.gz');A=[r for r in x4['rows'] if r['spec'].get('game_id')=='input4-rep1-A'];B=[r for r in x4['rows'] if r['spec'].get('game_id')=='input4-rep1-B'];correspond=[]
for a in A:
 for b in B:
  if all(a['identity'][k]==b['identity'][k] for k in ['key','history','legal_prefix','model']) and a['response']['body']['action']!=b['response']['body']['action']:correspond.append((a,b))
if correspond:
 for r in correspond[0]:root_summary(r['diagnostic']['validated_cp'],'reference')
final=load(BASE/'134-local-move-quality/final-results.json');scores=[]
for m in final['repeat_comparison']:scores.append({k:m[k] for k in ['input_index','branch','scores','same_exact_continuation','first_repeat_action_divergence_newply']})
derived_scores=[]
for m in final['repeat_comparison']:
 gs=sorted([g for g in final['games'] if g['input_index']==m['input_index'] and g['branch']==m['branch']],key=lambda g:g['rep']); vals=[1 if g['winner']==g['forced_side'] else (0.5 if g['winner'] is None else 0) for g in gs]; assert vals==m['scores']; derived_scores.append({'input':m['input_index'],'branch':m['branch'],'scores':vals,'basis':'saved final compact winner versus forced_side; no referee replay'})
assert len(final['games'])==8 and sum(g['new_public'] for g in final['games'])==276
out={'issue':'quoridor-4lc.136','run':os.environ.get('SIGMA_POLICY_RUN','saved136-unset'),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'roots132':roots,'roots134_input3_rep1_rep2_new3':rep,'input4_rep1_corresponding_different_Action_roots':len(correspond)*2,'input4_missing':'no matching key/history/prefix; different branch trajectories not sameinput control' if not correspond else None,'root_read_count':6+(2 if correspond else 0),'scores134':scores,'scores134_compact_recalculated':derived_scores,'selected_same_root_SAB_completed_progress':common_progress,'progress_limits':'SAB publication Action and completed count only; deep numeric and CPU missing; no additional roots read','quantity_not_CPU':True,'NN':0,'games':0,'actual_go':False,'input_hashes':refs}
(D/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
