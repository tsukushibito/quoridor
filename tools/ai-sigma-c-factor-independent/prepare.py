import pathlib,json,hashlib,difflib,datetime,os
R=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');T=R/'tools/ai-sigma-c-factor-independent';P=R/'.artifacts/ai-sigma/resume-20261002/C-FACTOR-BROWSER';O=R/'.artifacts/ai-sigma/resume-20261002/C-FACTOR-INDEPENDENT';U=R/'tools/ai-sigma-c-factor-browser'
s=(U/'runner.py').read_text().replace('C-FACTOR-BROWSER','C-FACTOR-INDEPENDENT').replace('quoridor-4lc.110','quoridor-4lc.111').replace('c110-','c111-').replace('110-c-factor-browser','111-c-factor-independent');s=s.replace("assert PHASE in ['browser-preflight','browser-diagnostic','browser-pair','protocol','build','count']","assert PHASE in ['browser-preflight','protocol','count']").replace("STORAGE_GUARD=469762048 if PHASE=='build' else 117440512","STORAGE_GUARD=29360128").replace("MAX_WALL=600 if PHASE=='build' else 60 if CPU==0 else 600","MAX_WALL=60 if CPU==0 else 300").replace("TOTAL_WALL=900 if PHASE=='build' else 600 if CPU==0 else 1800","TOTAL_WALL=300 if CPU==0 else 900")
(T/'runner.py').write_text(s)
s=(U/'browser.cjs').read_text().replace("__dirname+'/factor-worker.js'","path.resolve(__dirname,'../ai-sigma-c-factor-browser/factor-worker.js')").replace("__dirname+'/factor-main.js'","path.resolve(__dirname,'../ai-sigma-c-factor-browser/factor-main.js')").replace("ROOT+'/.artifacts/ai-sigma/resume-20261002/C-FACTOR-BROWSER/build/'","ROOT+'/.artifacts/ai-sigma/resume-20261002/C-FACTOR-INDEPENDENT/build/'")
(T/'browser.cjs').write_text(s)
s=(U/'diagnose.cjs').read_text().replace('C-FACTOR-BROWSER','C-FACTOR-INDEPENDENT').replace('quoridor-4lc.110','quoridor-4lc.111')
s=s.replace("save('classification-factor-mock',await browser.page.evaluate(()=>classificationFactorMock()));","save('classification-factor-mock',await browser.page.evaluate(()=>classificationFactorMock()));\n    await browser.page.addScriptTag({path:__dirname+'/independent-browser.js'});\n    save('independent-classification',await browser.page.evaluate(()=>independentClassification111()));\n    if(config.independent_saved){const savedJSON=fs.readFileSync(OUT+'/saved-browser-input.json','utf8');save('independent-saved-audit',await browser.page.evaluate(async ({savedJSON,fixtures,references})=>auditAll111(JSON.parse(savedJSON),fixtures,references),{savedJSON,fixtures,references}));}")
s=s.replace("rows=result.rows??[];save('browser-result',result);save('rows',rows);","rows=result.rows??[];save('browser-result',result);save('rows',rows);\n      save('independent-count-audit',await browser.page.evaluate(({result,config,fixtures,references})=>auditCounts111(result.count_results.map(r=>({...r,variant:config.variant})),fixtures,references),{result,config,fixtures,references}));\n      if(config.compare_independent){const prior=config.compare_independent.map(run=>{const c=JSON.parse(fs.readFileSync(OUT+'/runs/'+run+'/config.json'));const r=JSON.parse(fs.readFileSync(OUT+'/runs/'+run+'/browser-result.json'));return r.count_results.map(v=>({...v,variant:c.variant}));}).flat();const combinedJSON=JSON.stringify([...prior,...result.count_results.map(v=>({...v,variant:config.variant}))]);save('independent-four-comparison',await browser.page.evaluate(({combinedJSON,fixtures,references})=>auditCounts111(JSON.parse(combinedJSON),fixtures,references),{combinedJSON,fixtures,references}));}")
(T/'driver.cjs').write_text(s)
for name,old in [('runner.py','runner.py'),('browser.cjs','browser.cjs'),('driver.cjs','diagnose.cjs')]:
 (O/(name+'.adapter.diff')).write_text(''.join(difflib.unified_diff((U/old).read_text().splitlines(True),(T/name).read_text().splitlines(True),fromfile='original110/'+old,tofile='critic111/'+name)))
runs=[];counts=[];parity=[];ledger={}
def readpath(p):
 b=p.read_bytes();ledger[str(p.relative_to(R))]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return json.loads(b)
for name in ['c110-count-baseline-first-r1','c110-count-c1-first-r1','c110-count-baseline-last-r1','c110-count-c1-last-r1']:
 c=readpath(P/'runs'/name/'config.json');d=readpath(P/'runs'/name/'browser-result.json');counts +=[{**r,'variant':c['variant'],'run':name} for r in d['count_results']]
for name in ['c110-parity-original-r1','c110-parity-baseline-r1']:
 c=readpath(P/'runs'/name/'config.json');d=readpath(P/'runs'/name/'browser-result.json');parity +=[{**r,'variant':c['variant'],'run':name} for r in d['count_results']]
for name in ['c110-baseline-public-r1','c110-initial-pair-r1','c110-asym-pair-r1']:
 c=readpath(P/'runs'/name/'config.json');d=readpath(P/'runs'/name/'browser-result.json');chosen=set();seen=set()
 for row in d['rows']:
  key=(row['identity']['engine'],len(row['identity']['legal_prefix'])%2)
  if key not in seen or not row['response']['body']['completed']:chosen.add(row['identity']['request_id']);seen.add(key)
 rr=[]
 for row in d['rows']:
  diag=row['diagnostic'];new={k:v for k,v in row.items() if k not in ['diagnostic','gate']};new['diagnostic']={k:diag[k] for k in ['NN','sab_publications','validation_events','producer_markers'] if k in diag}
  if row['identity']['request_id'] in chosen:new['selected_numeric']={'numeric':diag['numeric'][0],'cp':diag.get('validated_cp')}
  if not row['response']['body']['completed']:new['null_timing_raw']={k:v for k,v in diag.items() if k in ['result','direct','producer_markers','validation_events','worker_done_ms']}
  rr.append(new)
 runs.append({'run':name,'rows':rr,'games':d.get('games',[]),'config':c,'clock_end':readpath(P/'runs'/name/'clock-end.json')})
input={'runs':runs,'counts':counts,'parity':parity};(O/'saved-browser-input.json').write_text(json.dumps(input,separators=(',',':'))+'\n');(O/'saved-input-before.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'initial_stopped_paths_not_final_data_Git':True,'checks':ledger},indent=2)+'\n')
base={'issue':'quoridor-4lc.111','frame':7,'kind':'count','processing_deadline':'2026-10-02T09:18:00Z','newjob_deadline':'2026-10-02T09:13:00Z','Git':None,'count_timeout_ms':30000,'T_ms':500,'adopt_ms':411,'sample_interval_ms':8,'dynamic_plies':0,'schedule':[],'diagnostic':True,'seed':1979}
settings=[('c111-asym-baseline-r1','baseline',['asym-hv-p2']),('c111-c1-r1','c1',['asym-hv-p2','straight-jump-p2']),('c111-jump-baseline-r1','baseline',['straight-jump-p2'])]
for i,(name,variant,fixtures) in enumerate(settings):
 c={**base,'run_id':name,'variant':variant,'count_searches':[{'fixture_id':f,'K':32} for f in fixtures],'independent_saved':i==0}
 if i==2:c['compare_independent']=[settings[0][0],settings[1][0]]
 (O/(name+'.config.json')).write_text(json.dumps(c,indent=2)+'\n')
(O/'preregister.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':'quoridor-4lc.111','primary_order':[{ 'run':name,'variant':v,'fixtures':f,'K':32} for name,v,f in settings],'primary_searches':4,'maximum_including_debug':12,'maximum_backups':384,'count_timeout_ms':30000,'new_games':0,'startup_separate_6_per_session':True,'coefficient_model_search_clock_not_modified':True},indent=2)+'\n')
print(json.dumps({'saved_input_bytes':(O/'saved-browser-input.json').stat().st_size,'counts':len(counts),'parity':len(parity),'rows':sum(len(r['rows']) for r in runs)}))
