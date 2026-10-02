from pathlib import Path
import json,tarfile,hashlib,datetime,os,subprocess,difflib
R=Path.cwd();T=R/'tools/ai-sigma-cpu-sigma-independent';O=R/'.artifacts/ai-sigma/resume-20261002/CPU-SIGMA-INDEPENDENT';D=R/'research-data/ai-sigma/117-cpu-sigma-comparison'
def H(b):return hashlib.sha256(b).hexdigest()
expected=['3a436997aa33994753e089b5ff03f59a2308e0c4794d24d74bb9e050d4d57c94','a82b4d3e82842d0c3540f78d28212901d30c34d95a0a41dff5746945b507a239','150de8c86b36a99aa3ab0f299f25410e853456bfbd2d52bf8f7ccabc7959b27e','31e64bc8772829b841ffc73ce028b5c2dac8c53ee1737084c6d6e7e9f0ec4f3b','a744238b43b0900ea245b34d9e564fe5f1fcfa4a07c9be68a9d34d1e3b2c73d4','07b78c7d1990137b945c09cb921a9bd19aef9b7bbb760e2ec811f3639f35a854']
(O/'selection-preregister.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':'quoridor-4lc.118','numeric_rule':'first row for each engine in each pair, no outcome selection, max12','clock_replay':'all saved12games/644rows','NN':0,'new_games':0},indent=2))
checks={};runs=[]
for i,h in enumerate(expected,1):
 name=f'cpu117-pair{i}-r1';p=D/(name+'.tar.gz');assert H(p.read_bytes())==h
 manifest=json.loads((D/(name+'.manifest.json')).read_text());by={x['path']:x['SHA256'] for x in manifest['members']};checks[str(p.relative_to(R))]=h
 with tarfile.open(p) as tf:
  def read(n):
   b=tf.extractfile(n).read();assert H(b)==by[n],n;checks[name+':'+n]=H(b);return json.loads(b)
  j=read(f'runs/{name}/browser-result.json');end=read(f'runs/{name}/clock-end.json');seen=set()
  for r in j['rows']:
   d=r['diagnostic'];engine=r['identity']['engine'];sample=engine not in seen;seen.add(engine)
   if sample:r['selected_numeric']={'numeric':d['numeric'][0],'cp':d.get('validated_cp')}
   r['diagnostic']={k:d.get(k) for k in ['identity','NN_control_events','sab_publications','validation_events','player_binding','worker_engine','control_final']}
  runs.append({'run':name,'pair':i,'seed':1979 if i<4 else 2098,'fixture':['initial-p1','asym-hv-p2','straight-jump-p2'][(i-1)%3],'rows':j['rows'],'games':j['games'],'startup_rows':j['startup_rows'],'started_requests':j['started_requests'],'started_games':j['started_games'],'waiting_messages':j['waiting_messages'],'main_timer_count':j['main_timer_count'],'external_abort':j['external_abort'],'player_errors':j['player_errors'],'player_status':j['player_status'],'clock_end':end})
  for n in [f'runs/{name}/source-bindings.json',f'runs/{name}/model-drop.json',f'runs/{name}/controlled-stop.json']:
   if n in by:
    x=read(n);(O/(name+'-'+Path(n).name)).write_text(json.dumps(x,indent=2))
(O/'saved-input.json').write_text(json.dumps({'runs':runs},separators=(',',':')))
pr=D/'preregister.json';assert H(pr.read_bytes())=='02d2df0dab87a99b31558961b54d93c8d25b0f9890c1e883ddaa2c3ca1b1eaa0';checks[str(pr.relative_to(R))]=H(pr.read_bytes())
s=D/'runtime-source-stopped-before-report.json';assert H(s.read_bytes())=='3998fe143ee2052d65118e611bc70cb57a909f6301f7894a6a58f87d1eed2c1b';stop=json.loads(s.read_text());checks[str(s.relative_to(R))]=H(s.read_bytes());live=[]
for x in stop['identities']:
 try:
  tick=x.get('starttick',x.get('start_ticks'));pid=x['pid'];current=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]);
  if current==int(tick):live.append(x)
 except FileNotFoundError:pass
assert not live
(O/'input-before.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'owner_stop':str(s),'recorded':len(stop['identities']),'current_same_identity':live,'original_data_final_handoff_pending':True,'saved_input_bytes':(O/'saved-input.json').stat().st_size},indent=2))
# Reuse the existing dedicated launcher only as resource/ownership machinery.
a=(R/'tools/ai-sigma-player-workers-independent/runner.py').read_text();b=a.replace('PLAYER-WORKERS-INDEPENDENT','CPU-SIGMA-INDEPENDENT').replace('113-player-workers-independent','118-cpu-sigma-independent').replace('quoridor-4lc.113','quoridor-4lc.118').replace("CONFIG['frame']==7","CONFIG['frame']==8").replace('p113-','p118-').replace('TOTAL_WALL=120 if CPU==0 else 360','TOTAL_WALL=180 if CPU==0 else 360')
(T/'runner.py').write_text(b);(O/'runner-adapter.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True))))
# Numeric helper is independently authored in109/113, not117's aggregator.
a=(R/'tools/ai-sigma-player-workers-independent/checker.js').read_text();b=a[:a.index('async function audit113')];(T/'numeric.js').write_text(b)
(O/'config.json').write_text(json.dumps({'issue':'quoridor-4lc.118','frame':8,'kind':'browser-preflight','run_id':'p118-saved-r1','processing_deadline':'2026-10-02T11:55:58Z','newjob_deadline':'2026-10-02T11:50:58Z'},indent=2))
print(json.dumps({'archives':6,'selected':12,'inputbytes':(O/'saved-input.json').stat().st_size,'identity_current0':len(stop['identities']),'inputchecks':len(checks)}))
