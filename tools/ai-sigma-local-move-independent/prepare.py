import pathlib,json,tarfile,hashlib,datetime,subprocess
R=pathlib.Path(__file__).resolve().parents[2];T=R/'tools/ai-sigma-local-move-independent';O=R/'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-INDEPENDENT';D=R/'research-data/ai-sigma/134-local-move-quality';H=lambda b:hashlib.sha256(b).hexdigest()
plan={'issue':'quoridor-4lc.135','receipt':'2026-10-02T17:09:42.015555696Z','kind':'count','frame':9,'run_id':'p135-saved-r1','processing_deadline':'2026-10-02T17:39:42Z','newjob_deadline':'2026-10-02T17:34:42Z','root_selection':'first saved public root of each of eight rollout ids, metadata only selection, max8, before numeric read','new_NN_model_game':0,'forecast_bytes':4194304};(O/'config.json').write_text(json.dumps(plan,indent=2)+'\n')
pr=R/'research-data/ai-sigma/134-local-move-quality/preregister.json';assert H(pr.read_bytes())=='355d9064f13caac54b5c20b23c523a834db58f49c9d0a4246afe40546fe1289d'
original_bytes=subprocess.check_output(['git','show','9c8224a:research-data/ai-sigma/134-local-move-quality/preregister.json'],cwd=R);assert H(original_bytes)=='a3b368a42a3d0efdbac8eb085f4c12db7c10de5e55f31ec9891ddec8de666a38';original=json.loads(original_bytes);executed=json.loads(pr.read_text())
for k in original:
 if k not in ['selected','source_CP_tree_readonly_not_copied']:assert original[k]==executed[k],k
for a,b in zip(original['selected'],executed['selected']):
 for branch in ['A','B']:
  for k in a[branch]:
   if k=='cp':
    for c in a[branch]['cp']:
     if c!='tree':assert a[branch]['cp'][c]==b[branch]['cp'][c],c
   else:assert a[branch][k]==b[branch][k],k
 assert a['fixture']==b['fixture']
(O/'preregister-binding.json').write_text(json.dumps({'original_Git':'9c8224a','original_SHA256':H(original_bytes),'executed_SHA256':H(pr.read_bytes()),'difference':'nonroot CP tree removal plus corresponding annotation only; ordering/conditions/fixtures/rootCP unchanged','initial_helper_hash_assumption_failure':True},indent=2)+'\n');f=R/'research-data/ai-sigma/132-deep-node-comparison/fixed-inputs.json';assert H(f.read_bytes())=='fffc171a2b2fc5f36cab950299e651912fa95287ee0e6121bebb35d18bf56b01'
checks={str(pr.relative_to(R)):H(pr.read_bytes()),str(f.relative_to(R)):H(f.read_bytes())};runs=[];small=[];samples=[]
for i,runid in enumerate(['quality134-group1-r3','quality134-group2-r1','quality134-group3-r1','quality134-group4-r1'],1):
 man=json.loads((D/(runid+'-archive-manifest.json')).read_text());p=D/(runid+'.tar.gz');assert H(p.read_bytes())==man['SHA256'];checks[str(p.relative_to(R))]=man['SHA256'];by={m['path']:m['SHA256'] for m in man['members']}
 with tarfile.open(p) as a:
  def read(n):
   b=a.extractfile(n).read();assert H(b)==by[n];checks[runid+':'+n]=H(b);return json.loads(b)
  x=read('runs/'+runid+'/browser-result.json');end=read('runs/'+runid+'/clock-end.json');config=read('runs/'+runid+'/config.json');sel={g['turn_indices'][0] for g in x['games']};samples+=sorted(sel)
  for r in x['rows']:
   d=r['diagnostic'];r['selected_numeric']={'numeric':d['numeric'][0],'cp':d['validated_cp']} if r['identity']['request_id'] in sel else None
   r['diagnostic']={k:d.get(k) for k in ['identity','NN_control_events','sab_publications','validation_events','player_binding','worker_engine','control_final','discarded_snapshots']}
   for k in ['gate']:r.pop(k,None)
  runs.append({'run':runid,'source_Git':man['source_Git'],'clock_end':end,'config':config,**x})
  ss={}
  for n in ['source-bindings','finally-model-drop','main-timers-stop','outer-controlled-stop','pause-monitor-stop','startup']:
   ss[n]=read('runs/'+runid+'/'+n+'.json')
  small.append({'run':runid,'source_Git':man['source_Git'],'small':ss})
assert len(samples)==8
(O/'saved-input.json').write_text(json.dumps({'runs':runs,'fixed':json.loads(f.read_text()),'preregister':json.loads(pr.read_text())},separators=(',',':')))
stop=D/'runtime-source-stopped-before-report.json';checks[str(stop.relative_to(R))]=H(stop.read_bytes())
(O/'input-before.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'selection':samples,'rule_before_numeric_read':plan['root_selection'],'source_and_stop':small,'initial_final_handoff_not_yet_bound':True,'stop_SHA':H(stop.read_bytes())},indent=2)+'\n')
print(json.dumps({'groups':4,'roots_selected':8,'compact_bytes':(O/'saved-input.json').stat().st_size,'necessary_hashes':len(checks),'stopSHA':H(stop.read_bytes())}))
