from pathlib import Path
import json,tarfile,hashlib,datetime,os,difflib
R=Path.cwd();T=R/'tools/ai-sigma-player-workers-independent';O=R/'.artifacts/ai-sigma/resume-20261002/PLAYER-WORKERS-INDEPENDENT';U=R/'tools/ai-sigma-player-workers';D=R/'research-data/ai-sigma/112-player-workers'
checks={}; stop=json.loads((D/'runtime-source-stopped-before-report.json').read_text())
for path,h in stop['source_after_hashes'].items():
 if isinstance(h,dict):h=h.get('sha256')
 checks[path]={'expected':h,'actual':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
assert all(v['expected']==v['actual'] for v in checks.values())
live=[]
for x in stop['identity_union']:
 try:
  if int(Path(f"/proc/{x['pid']}/stat").read_text().split(') ')[1].split()[19])==int(x['starttick']):live.append(x)
 except FileNotFoundError:pass
assert not live
runs=[];memberchecks=[]
manifest=json.loads((D/'archive-manifest.json').read_text());by={x['path']:x for x in manifest['entries']}
with tarfile.open(D/'run-evidence.tar.gz') as tf:
 for run in ['p112-functional-r1','p112-initial-pair-r1','p112-asym-pair-r1']:
  n=f'runs/{run}/browser-result.json';b=tf.extractfile(n).read();assert hashlib.sha256(b).hexdigest()==by[n]['sha256'];memberchecks.append(n);j=json.loads(b)
  rows=[];selected=set()
  for r in j['rows']:
   d=r['diagnostic'];key=(r['identity']['engine'],len(r['identity']['legal_prefix'])%2,r['response']['body']['cancelled']);sample=key not in selected;selected.add(key)
   r['diagnostic']={'NN_control_events':d['NN_control_events'],'sab_publications':d['sab_publications'],'control_final':d.get('control_final'),'discarded_snapshots':d.get('discarded_snapshots')}
   if sample:r['selected_numeric']={'numeric':d['numeric'][0],'cp':d.get('validated_cp')}
   rows.append(r)
  endname=f'runs/{run}/clock-end.json';b=tf.extractfile(endname).read();assert hashlib.sha256(b).hexdigest()==by[endname]['sha256'];memberchecks.append(endname)
  runs.append({'run':run,'rows':rows,'games':j.get('games',[]),'clock_end':json.loads(b)})
  if run=='p112-functional-r1': config=json.loads(tf.extractfile('runs/'+run+'.config.json').read())
(O/'saved-input.json').write_text(json.dumps({'runs':runs},separators=(',',':')))
for n in ['runner.py','browser.cjs','diagnose.cjs']:
 s=(U/n).read_text();a=s
 if n=='runner.py':
  s=s.replace('PLAYER-WORKERS/runs','PLAYER-WORKERS-INDEPENDENT/runs').replace('112-player-workers','113-player-workers-independent').replace('quoridor-4lc.112','quoridor-4lc.113').replace('p112-','p113-').replace('STORAGE_GUARD=58720256','STORAGE_GUARD=29360128').replace("MAX_WALL=600 if PHASE=='build' else 60 if CPU==0 else 600","MAX_WALL=60 if CPU==0 else 180").replace("TOTAL_WALL=900 if PHASE=='build' else 600 if CPU==0 else 1800","TOTAL_WALL=120 if CPU==0 else 360")
 elif n=='browser.cjs':
  s=s.replace("__dirname+'/player-main.js'","path.resolve(__dirname,'../ai-sigma-player-workers/player-main.js')").replace("__dirname+'/player-worker.js'","path.resolve(__dirname,'../ai-sigma-player-workers/player-worker.js')").replace("__dirname+'/player-control.cjs'","path.resolve(__dirname,'../ai-sigma-player-workers/player-control.cjs')")
 else:
  s=s.replace('PLAYER-WORKERS\'','PLAYER-WORKERS-INDEPENDENT\'').replace('quoridor-4lc.112','quoridor-4lc.113')
  s=s.replace("save('player-routing-mock',await browser.page.evaluate(()=>playerRoutingMock()));","save('player-routing-mock',await browser.page.evaluate(()=>playerRoutingMock()));\n    await browser.page.addScriptTag({path:__dirname+'/checker.js'});\n    save('independent-mock',await browser.page.evaluate(()=>independentMock109()));\n    const savedText=fs.readFileSync(OUT+'/saved-input.json','utf8');\n    save('independent-saved',await browser.page.evaluate(({text,fixtures,references})=>audit113(JSON.parse(text),fixtures,references),{text:savedText,fixtures,references}));")
  s=s.replace("save('browser-result',result);","save('browser-result',result);save('independent-runtime',await browser.page.evaluate(({text,fixtures,references})=>audit113({runs:[{run:'p113-runtime',...JSON.parse(text)}]},fixtures,references),{text:JSON.stringify(result),fixtures,references}));")
 (T/n).write_text(s);(O/(n+'.diff')).write_text(''.join(difflib.unified_diff(a.splitlines(True),s.splitlines(True),fromfile=str(U/n),tofile=str(T/n))))
config.update(issue='quoridor-4lc.113',run_id='p113-functional-r1',Git='uncommitted adapter of 3682ab7',processing_deadline='2026-10-02T10:02:48Z',newjob_deadline='2026-10-02T09:57:48Z')
(O/'config.json').write_text(json.dumps(config,indent=2));(O/'preregister.json').write_text(json.dumps({'issue':'quoridor-4lc.113','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'schedule':config['schedule'],'dynamic_plies':4,'functional_public_max':7,'startup_NN':6,'model_sessions':2,'C':1.5,'NNthreads':1,'CPU':[2],'producer_Git':'3682ab7b520024735e79e42eea79c982897c3957','new_games':0,'condition_changes':False},indent=2))
(O/'input-before.json').write_text(json.dumps({'source':checks,'owner_current_identity_count':len(stop['identity_union']),'live':live,'memberchecks':memberchecks,'raw_schema':list(runs[0]['rows'][0]),'saved_input_bytes':(O/'saved-input.json').stat().st_size},indent=2));print('prepared', (O/'saved-input.json').stat().st_size)
