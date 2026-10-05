import collections,datetime,difflib,hashlib,json,math,pathlib,struct,subprocess,tarfile
R=pathlib.Path(__file__).resolve().parents[2];P=R/'research-data/ai-sigma/140-candidate-true-mean-fpu';D=R/'research-data/ai-sigma/141-true-mean-fpu-saved-independent'
checks=[];refs=[]
def ck(name,c):checks.append({'check':name,'pass':bool(c)})
def sha(b):return hashlib.sha256(b).hexdigest()
def fixed(name,expected=None,git='648695cd68a8e9c0609deb649b9f08fc058cd3ce'):
 b=(P/name).read_bytes();ck('Gitblob '+name,b==subprocess.check_output(['git','show',git+':'+str((P/name).relative_to(R))]))
 if expected:ck('SHA '+name,sha(b)==expected)
 refs.append({'path':str((P/name).relative_to(R)),'SHA256':sha(b),'Git':git});return json.loads(b)
manifest=fixed('archive-manifest.json');arc=P/'all-runs-failures.tar.gz';ck('archive SHA',sha(arc.read_bytes())=='1fd8e4483e0e95b7f42ec92b2898a88d717e31f0de5b33e04751019fff69c427')
refs.append({'path':str(arc.relative_to(R)),'SHA256':sha(arc.read_bytes())});member={m['path']:m for m in manifest['members']};a=tarfile.open(arc)
def raw(name,binary=False):
 b=a.extractfile(name).read();m=member[name];ck('member '+name,len(b)==m['bytes'] and sha(b)==m['SHA256']);refs.append({'member':name,'SHA256':sha(b),'bytes':len(b)});return b if binary else json.loads(b)
handoff=fixed('handoff-summary.json','c8b19af2fa918237b786474aac4f781fd2c18d7fb549a4f2616639e207e6bd68')
stop=fixed('runtime-source-stopped-before-report.json','16a3f57c2d38ebe046d364145ed292355ad352e164494791ba83d84db9e0c136')
binding=fixed('source-input-binding.json');dep=fixed('dependency-binding-final.json');served=fixed('served-source-binding-final.json');plan=fixed('preregister.json');fixtures=fixed('fixed-inputs.json')['fixtures'];failures=fixed('failures.json');closure=fixed('closure-failures.json')
data=raw('runs/fpu140-mechanism-r1/browser-result.json');mock=raw('mock.json');rows=data['mean_results'];ck('six fixed order',len(rows)==6 and [(r['fixture_id'],r['variant']) for r in rows]==[(s['fixture_id'],s['variant']) for s in plan['mechanism_order']]);ck('finished no errors',not data['errors'] and data['started_requests']==data['completed_requests']==6 and not data['games'])
def f(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def bits(x):return struct.unpack('<f',struct.pack('<I',x))[0]
def near(x,y):return abs(x-y)<=1e-6+1e-6*abs(y)
def tie(action):
 x=1979^action; mask=(1<<64)-1;x=((x^(x>>30))*0xbf58476d1ce4e5b9)&mask;x=((x^(x>>27))*0x94d049bb133111eb)&mask;return x^(x>>31)
def decoded(node):return [[e[0],bits(e[1]),e[2],bits(e[3])] for e in node['edges']]
summaries=[];ledgers=[];ancestor=[]
for row in rows:
 cp=row['cp'];cs=row['CPs'];n=row['numeric'][0];ck('K32/NN32/edge31',len(cs)==row['completed_backups']==row['NN_calls']==cp['simulations']==32 and sum(e[2] for e in cp['root_edges'])==row['edge_sum']==31 and row['rootN']==32 and row['terminal_noNN_backups']==0 and not row['primary'])
 ck('root shape finite strict',len(n['features_bits'])==648 and len(n['policy_logits'])==136 and all(math.isfinite(x) for x in n['policy_logits']) and -1<=n['value']<=1)
 for k,p in enumerate(cs,1):
  p=p['cp'];ck('all completed CP root count',p['simulations']==p['nn_calls']==k and sum(e[2] for e in p['root_edges'])==k-1 and not p['cap'])
  best=max(p['root_edges'],key=lambda e:(e[2],e[1],-tie(e[0])));ck('all CP finish visit/prior/tie',best[0]==p['action'])
 t=row['trace'];selects=t['selections'] if t else [];rootselect=[s for s in selects if s['node_index']==0]
 if t:
  running={};events=collections.defaultdict(list)
  for e in t['visits']:
   idx=e['node_index'];old=running.get(idx,(0,0.0));ck('actual node visit once f32',old==(e['preN'],e['preSum']) and e['postN']==e['preN']+1 and f(e['preSum']+e['value_own_side'])==e['postSum']);running[idx]=(e['postN'],e['postSum']);events[e['sim_completed_before']].append(e)
  for k,es in events.items():
   leaf=es[0];ck('ancestor actual turn/sign',all(e['value_own_side']==(leaf['value_own_side'] if e['turn']==leaf['turn'] else -leaf['value_own_side']) for e in es) and len({e['node_index'] for e in es})==len(es))
  for s in selects:
   k=s['sim_completed_before'];idx=s['node_index'];prev=[e for e in t['visits'] if e['node_index']==idx and e['sim_completed_before']<k];node=cp['tree'][idx];edges=decoded(node)
   for edge in edges:
    prior_choices=[x for x in selects if x['node_index']==idx and x['Action']==edge[0] and x['sim_completed_before']<k]
    edge[2]=len(prior_choices);edge[3]=0.0
    for x in prior_choices:
     event=next(e for e in events[x['sim_completed_before']] if e['node_index']==idx)
     edge[3]=f(edge[3]+event['value_own_side'])
   mean=f(f(s['node_value_sum'])/s['nodeN']);mass=0.0
   for e in edges:
    if e[2]>0:mass=f(mass+e[1])
   fpu=f(mean-f(f(.2)*f(math.sqrt(mass))));chosen=next(e for e in edges if e[0]==s['Action'])
   ck('all select actual mean ledger',len(prev)==s['nodeN'] and prev[-1]['postSum']==s['node_value_sum'] and mean==s['true_mean'] and s['FPU_enabled']==(row['variant']=='fpu') and not s['N0_mean_missing'] and s['visited']==(chosen[2]>0))
   ck('all select visited original prior',mass==s['visited_original_prior_sum'] and near(fpu,s['fpu']) and chosen[1:]==[s['prior'],s['edge_visits'],s['edge_value_sum']])
   scores=[]
   for e in edges:
    q=f(e[3]/e[2]) if e[2] else (fpu if row['variant']=='fpu' else 0.0)
    score=f(q+f(f(f(1.5*e[1])*f(math.sqrt(f(s['nodeN']+1))))/f(e[2]+1)))
    scores.append((score,e[0],q))
   best=max(scores,key=lambda z:(z[0],-tie(z[1])))
   ck('all select PUCT score/winner',best[1]==s['Action'] and near(best[0],s['actual_score']) and near(best[2],s['actual_q']))
  for node in t['nodes']:
   pre=node['pre'];post=node['post_path'];v=node['leaf_side_value'];ck('selected leaf actual backup',node['post_leaf_visits']==pre['leaf_visits']+1 and f(pre['leaf_true_sum']+v)==node['post_leaf_true_sum'])
   for before,after in zip(reversed(pre['path']),reversed(post)):
    v=-v;ck('selected ancestor backup delta',before['parent_index']==after['parent_index'] and before['Action']==after['Action'] and after['edge_visits']==before['edge_visits']+1 and after['parent_visits']==before['parent_visits']+1 and f(before['edge_value_sum']+v)==after['edge_value_sum'] and f(before['parent_true_sum']+v)==after['parent_true_sum'])
  ck('final node mean ledger',all(running[node['index']]==(node['visits'],node['true_value_sum']) for node in cp['tree']))
  ledgers.append({'fixture':row['fixture_id'],'variant':row['variant'],'selects':len(selects),'visits':len(t['visits']),'root_selects':len(rootselect)})
 probabilities=[e[2]/31 for e in cp['root_edges'] if e[2]]
 summaries.append({'fixture':row['fixture_id'],'variant':row['variant'],'Action':cp['action'],'K':32,'edge_sum':31,'NN':row['NN_calls'],'depth':cp['max_depth'],'cap':cp['cap'],'root_entropy':-sum(p*math.log(p) for p in probabilities),'root_unvisited_selects':sum(not s['visited'] for s in rootselect) if t else None,'true_mean':f(cp['tree'][0]['true_value_sum']/32) if t else None,'original_mean_missing':not t})
parity=[];first=[];shared=[];contrasts=[]
for fid in dict.fromkeys(r['fixture_id'] for r in rows):
 old,q,fp=[next(r for r in rows if r['fixture_id']==fid and r['variant']==v) for v in ['original','q0','fpu']]
 nk=['features_bits','policy_logits','value'];equal=all(old['numeric'][0][k]==q['numeric'][0][k] for k in nk)
 fields=['action','root_edges','simulations','nn_calls','max_depth','cap','nodes_count','edges_count','policy_fallbacks','value_fallbacks']
 equal=equal and all(all(o['cp'][k]==n['cp'][k] for k in fields) for o,n in zip(old['CPs'],q['CPs']));ck('original Q0 all32 CP parity',equal);parity.append({'fixture':fid,'all32_exact':equal,'arena_equal':old['cp']['arena_bytes']==q['cp']['arena_bytes'],'new_mean_original_missing':True})
 qs={s['sim_completed_before']:s for s in q['trace']['selections'] if s['node_index']==0};fs={s['sim_completed_before']:s for s in fp['trace']['selections'] if s['node_index']==0}
 k=next(k for k in range(1,32) if qs[k]['Action']!=fs[k]['Action']);first.append({'fixture':fid,'K_completed_before':k,'Q0':qs[k],'FPU':fs[k],'same_parent_mean_prior':qs[k]['true_mean']==fs[k]['true_mean'] and qs[k]['visited_original_prior_sum']==fs[k]['visited_original_prior_sum']})
 def key(n):return n['key'],n['ply'],tuple(sorted(map(tuple,n['history'])))
 match=[]
 for n in q['trace']['nodes']:
  other=next((m for m in fp['trace']['nodes'] if key(n)==key(m)),None)
  if other:
   ck('shared selected feature/side/NN',n['features_bits']==other['features_bits'] and n['turn']==other['turn'] and n['terminal']==other['terminal'] and all(n['numeric'][k]==other['numeric'][k] for k in ['policy_logits','value']));match.append(n['node_index'])
 shared.append({'fixture':fid,'Q0_selected':len(q['trace']['nodes']),'FPU_selected':len(fp['trace']['nodes']),'matched':len(match),'unshared_each':8-len(match),'general_deep_unrecognized':True})
 qe={e[0]:e for e in q['cp']['root_edges']};fe={e[0]:e for e in fp['cp']['root_edges']};contrasts.append({'fixture':fid,'Action_Q0':q['cp']['action'],'Action_FPU':fp['cp']['action'],'TV':sum(abs(qe[k][2]-fe[k][2]) for k in qe)/62})
ck('280 true mean selects',sum(x['selects'] for x in ledgers)==280)
mock_cases=[]
for probe in mock['probe']:
 for case in probe['cases']:
  for e in case.get('visits',[]):ck('artificial saved visit helper',e['postN']==e['preN']+1 and f(e['preSum']+e['value_own_side'])==e['postSum'])
  if case['case']=='ancestor_depth':ck('artificial ancestor alternating',all(e['postSum']==(.375 if (case['depth']-e['node_index'])%2==0 else -.375) for e in case['visits']))
  if case['case']=='duplicate_async_discard':ck('artificial duplicate not backup',case['double_backup'] is False)
  if case['case']=='artificial_expanded_N0':ck('artificial missing mean no division',case['selection'][0]['true_mean'] is None and case['selection'][0]['fpu'] is None and case['selection'][0]['actual_q']==0)
  mock_cases.append({'variant':probe['variant'],'case':case['case'],'artificial_not_midgame_terminal':True})
quality=next(r for r in rows if r['variant']=='fpu' and r['fixture_id']==plan['inputs'][0]['id'])
ck('preregister global adverse exit/quality0',quality['cp']['action']==133 and 'input3FPU133' in plan['quality_exit'] and data['branch']=='known_adverse_input3_end' and not data['games'])
source=[]
for p,h in binding['new_private'].items():
 b=(R/p).read_bytes();ck('private measured/source hash '+p,sha(b)==h==sha(subprocess.check_output(['git','show','25d673dcee7cde1516eb10445eb4611abebc20f7:'+p])));source.append({'path':p,'SHA256':sha(b)})
for build in binding['private_builds']:
 b=raw('build/'+build['variant']+'.wasm',True);ck('private binary build bind',sha(b)==build['SHA256'] and len(b)==build['bytes'])
binary=binding['original_binary'];ck('immutable baseline bytes',sha((R/binary['path']).read_bytes())==binary['SHA256'])
deps=[]
for info in dep['readonly_dependency_current_Git_files']:
 p=info['path']
 if '/tests/' in p or '/bin/' in p:continue
 b=(R/p).read_bytes();ck('shared readonly current hash '+p,sha(b)==info['SHA256']);deps.append({'path':p,'hash_match':True,'Git_equal':info['measured_Git_current_equal'],'current_mtime_equal':datetime.datetime.fromtimestamp((R/p).stat().st_mtime,datetime.timezone.utc).isoformat()==info['current_mtime_UTC'],'not_fullperiod_build_audit':True})
for patch in dep['uncommitted_current_library_diffs']:
 p=patch['path'];base=subprocess.run(['git','show','25d673d:'+p],capture_output=True).stdout.decode();now=(R/p).read_text();diff=''.join(difflib.unified_diff(base.splitlines(True),now.splitlines(True)));ck('saved shared patch/current '+p,diff==patch['diff'])
drop=raw('runs/fpu140-mechanism-r1/finally-model-drop.json');timers=raw('runs/fpu140-mechanism-r1/main-timers-stop.json');callback=raw('runs/fpu140-mechanism-r1/pause-monitor-stop.json');inner=raw('runs/fpu140-mechanism-r1/outer-controlled-stop.json');outer=raw('runs/fpu140-mechanism-r1.owned-ack.json')
startup=raw('runs/fpu140-mechanism-r1/startup.json');load=raw('runs/fpu140-mechanism-r1/model-load.json')
ck('startup6 separate/session2',sum(r['NN'] for r in startup['rows'])==startup['startup_NN']==6 and startup['model_sessions']==2 and all(r['zero'] for r in startup['rows']) and not startup['tree_history_cache_reused'])
ck('same model CPU1 no proxy',len(load['players'])==2 and len({p['digest'] for p in load['players']})==1 and all(p['threads']==1 and not p['proxy'] for p in load['players']))
qb,fb=binding['private_builds'];ck('only build flag factor',fb['command']==qb['command']+['--features','true-mean-fpu'] and qb['source']==fb['source'] and qb['RUSTFLAGS']==fb['RUSTFLAGS'] and qb['rustc']==fb['rustc'] and qb['cargo']==fb['cargo'])
ck('Model2 drop zero',len(drop['players'])==2 and drop['handles']==drop['activeNN']==0);ck('main timer/message zero',timers['main_timers']==0 and timers['pending_messages']==[]);ck('monitor callback stop',callback['all_owned_read_callbacks_waited'] and not callback['active_monitor_timer'] and not callback['pending_children']);ck('inner forced and outer wait',inner['forced'] and inner['waited'] and not inner['remaining_pids'] and not outer['registered_live'] and not outer['unknown_adopted'] and outer['kernel_boundary']['sole_explicit_root'])
ck('search6 zero',len(rows)==6 and all(not r['zero']['handles'] and not r['zero']['activeNN'] for r in rows))
current=[];errors=[];ck('same boot',stop['boot']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip())
for i in stop['identities']:
 try:s=pathlib.Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 except Exception as e:errors.append(str(e));continue
 if int(s[19])==i['start_ticks']:current.append(i)
ck('117 current identity absent',len(stop['identities'])==117 and not current and not errors)
ck('final source stopped',stop['source_write_stopped'] and not stop['report_preparation_source_still_active'])
for p,h in stop['source_hashafter_all_own'].items():ck('final hashafter '+p,sha((R/p).read_bytes())==h)
before=fixed('source-before.json');ck('source measured beforeafter',before['own']==stop['source_hashafter'] and before['readonly']==stop['necessary_readonly_current_hashes'])
result={'issue':'quoridor-4lc.141','checks':checks,'failed':[c for c in checks if not c['pass']],'rows':summaries,'all32_Q0_parity':parity,'actual_mean_selects':ledgers,'first_divergence':first,'shared_nodes':shared,'contrasts':contrasts,'artificial_fixture_cases':mock_cases,'dependency':deps,'Git_only_insufficient':True,'browser_independent_fetch_digest_missing':True,'build_fullperiod_read_audit_missing':True,'quality_rollouts':0,'input4_118_quality_missing':True,'hand_NN':192,'startup_NN':6,'new_NN_Chrome_build':0,'stop':{'117_current':current,'read_errors':errors,'source_stop':True,'inner_forced':inner['forced'],'outer_wait_zero':not outer['registered_live'] and not outer['unknown_adopted'],'Model2zero':drop['handles']==drop['activeNN']==0,'current_absence_not_natural_fullperiod':True},'refs':refs,'original_failures':failures,'closure_failures':closure}
(D/'independent-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['failed','rows','all32_Q0_parity','actual_mean_selects','first_divergence','shared_nodes','contrasts']}))
