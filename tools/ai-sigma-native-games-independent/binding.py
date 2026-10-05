import pathlib,json,hashlib,subprocess,datetime,struct
ROOT=pathlib.Path.cwd();D=ROOT/'research-data/ai-sigma/169-native-games-independent';O=ROOT/'research-data/ai-sigma/165-native-baseline';B=ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/runs'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(v,m):
 if not v:raise ValueError(m)
r=read(D/'replay-result.json');inputs=read(O/'stageB-inputs.json');out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_bindings':[],'jobs':[],'teachers':[],'current_exact_identity_present':[],'model':{},'clock_operation_gap':{'stamp_before_validation_and_clone':True,'actual_completion_unknown':True},'init':{'sessions':0,'ORT_init_ms':0,'startup_wall_ms':0,'startup_API_ms':0},'cost':{}}
require(sha(O/'stageB-inputs.json')=='7cd2fe2470792a9e1ac2de381ec8a89974f78c4844a943758ec82147c0c0a5d5','input hash')
games={};rows=[];jobwall=0
for i in range(1,9):
 run=f'native165-pair{i:02}-r1';raw=read(B/run/'result.json');p=read(B/(run+'.process.json'));ii=read(B/(run+'.inputs.json'));clocksource={}
 for name in ['arena.cjs','clock.cjs','engine.cjs','ort.py','game.js','context.js','reference-core-native.js']:
  path='tools/ai-sigma-native-baseline/'+name;blob=subprocess.check_output(['git','show',ii['git_commit']+':'+path]);h=hashlib.sha256(blob).hexdigest();require(h==ii['source'][str(ROOT/path)],'served source '+name);clocksource[name]=h
 out['source_bindings'].append({'run':run,'git':ii['git_commit'],'source_SHA':clocksource,'input_metadata_sha':sha(B/(run+'.inputs.json'))})
 require(p['exit']==0 and not p['remaining'] and not p['unknown_adopted'] and p['ledger_monitor_remaining_consistent'],'owned stop');require(p['assigned_CPU']==2 and p['all_observed_TIDs_at_assigned_CPU'] and not p['affinity_violations'],'sample affinity');require(p['peak_group_plus_runner_RSS']<p['guardRSS'],'RAM observed');jobms=(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds()*1000;jobwall+=jobms
 monitor=read(B/run/'pause-monitor-stop.json');require(monitor['all_owned_read_callbacks_waited'] and not monitor['pending_children'] and not monitor['active_monitor_timer'],'monitor stop')
 summary=read(B/run/'control-summary.json');require(not summary['primary'] and not summary['control'],'control stop')
 out['jobs'].append({'run':run,'job_wall_ms':jobms,'sampled_peak_RSS':p['peak_group_plus_runner_RSS'],'exit':p['exit'],'remaining':p['remaining'],'unknown_adopted':p['unknown_adopted'],'callbacks_waited':monitor['all_owned_read_callbacks_waited'],'timer_active':monitor['active_monitor_timer'],'process_sha':sha(B/(run+'.process.json'))})
 ids=[{'pid':p['runner_pid'],'start_ticks':p['runner_starttick']},{'pid':p['child_pid'],'start_ticks':p['child_starttick']}]
 for engine in ['candidate','reference']:
  init=raw['init'][engine];info=init['info'];require(info['providers']==['CPUExecutionProvider'] and info['version']=='1.30.0' and info['intra']==info['inter']==1 and info['sequential'] and info['affinity']==[2],'ORT metadata');require(init['startup']['count']==1,'startup');out['init']['sessions']+=1;out['init']['ORT_init_ms']+=info['init_ms'];out['init']['startup_wall_ms']+=init['startup']['wall_ms'];out['init']['startup_API_ms']+=init['startup']['API_ms'];ids+=init['identities'];close=raw['closed'][engine];require(close['exit']=={'code':0,'signal':None} and all(x=={'code':0,'signal':None} for x in close['receipt']['exit']),'modelengine close')
 for identity in ids:
  try:fields=pathlib.Path(f"/proc/{identity['pid']}/stat").read_text().rsplit(')',1)[1].split();same=int(fields[19])==int(identity['start_ticks'])
  except FileNotFoundError:same=False
  if same:out['current_exact_identity_present'].append(identity)
 for g in raw['games']:games[g['game_id']]=g
 rows +=[json.loads(l) for l in (B/run/'journal.jsonl').read_text().splitlines()]
require(not out['current_exact_identity_present'],'current process')
model=ROOT/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';out['model']={'sha':sha(model),'expected':'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'};require(out['model']['sha']==out['model']['expected'],'model')
# Pair linkage, value perspective, and pi rederived from captured immutable opening CP.
for l in (O/'opening-teachers.jsonl').read_text().splitlines():
 t=json.loads(l);g=games[t['source']['game']];root=g['firstRoot'];fixed=next(x['fixture'] for x in inputs['rows'] if x.get('fixture',{}).get('id')==g['fixture_id']);c=root['publicCP']['cp'];tv=t['teacher'];mapping=dict(t['mapping136']);pi=[0.]*136;visits=sum(e[2] for e in c['root_edges'])
 for e in c['root_edges']:pi[mapping[e[0]]]=e[2]/visits
 require(all(abs(a-b)<1e-14 for a,b in zip(pi,t['pi136'])) and abs(sum(pi)-1)<1e-14,'pi');require(t['edge_visits']==[[e[0],e[2]] for e in c['root_edges']],'edge visits');require(t['features_bits']==fixed['root_state']['features_bits'] and t['state']['history']==fixed['root_state']['history'],'teacher state');require(t['state']['side']==root['side']-1 and t['engine']==root['engine'],'teacher side');z=1 if g['winner']==root['side'] else -1;require(tv['game_z']==z and tv['game_z_p1']==(1 if g['winner']==1 else -1),'z perspective');value=struct.unpack('<f',struct.pack('<I',root['NN_bits'][-1]))[0];require(tv['root_nn_stm']==value and tv['rootmean_stm']==c['root_mean'] and tv['rootN']==c['root_visits'],'teacher value source');require(tv['leaf_nn'] is None,'no invented leaf');require(sha(ROOT/t['source']['raw'])==t['source']['raw_SHA256'],'teacher raw binding');out['teachers'].append({'game':g['game_id'],'pair':g['pair'],'group':t['group'],'split':t['split'],'z_stm':z,'rootN':c['root_visits'],'leaf_missing':True})
groups={}
for t in out['teachers']:groups.setdefault(t['group'],set()).add(t['split'])
require(len(out['teachers'])==16 and len(groups)==8 and all(len(s)==1 for s in groups.values()),'lineage split')
late_tail=[{k:x[k] for k in ['game_id','ply','engine','completed','terminal_noNN','CP_received','CP_admitted','CP_late_discarded','cleanup_after_public_ms']} for x in rows if x['cleanup_after_public_ms']>100]
out['cost']={'management_job_ms':jobwall,'games_ms':r['cost']['games_ms'],'arena_ms':r['cost']['arena_ms'],'startup_and_close_and_between_games_ms':r['cost']['arena_ms']-r['cost']['games_ms'],'outer_overhead_ms':jobwall-r['cost']['arena_ms'],'late_tail_rows':late_tail,'late_tail_cleanup_ms':sum(x['cleanup_after_public_ms'] for x in late_tail),'game_clock_1200_projection_hours':r['cost']['games_ms']/16*1200/3600000,'management_1200_projection_hours':jobwall/16*1200/3600000,'projection_not_speed_guarantee':True,'CP_bytes_not_captured':True}
out['teacher_sha']=sha(O/'opening-teachers.jsonl');out['erratum_sha']=sha(O/'clock-receipt-erratum.json');out['receipt_binding_sha']=sha(O/'stageB-receipt-source-binding.json');out['science_stop_sha']=sha(O/'science-stop.json');out['all_period_all_host_proof']=False;out['new_NN']=0
(D/'binding-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['cost','init','current_exact_identity_present']}))
