import pathlib,json,hashlib,subprocess,datetime
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-INDEPENDENT';D=R/'research-data/ai-sigma/134-local-move-quality';H=lambda b:hashlib.sha256(b).hexdigest();h=json.loads((D/'handoff-summary.json').read_text());g=h['data_report_Git'];hg=subprocess.check_output(['git','log','-1','--format=%H','--',str((D/'handoff-summary.json').relative_to(R))],cwd=R,text=True).strip();checks=[]
for n in ['handoff-summary.json','runtime-source-stopped-before-report.json','preregister.json','final-results.json']:
 p=D/n;b=p.read_bytes();git=hg if n=='handoff-summary.json' else g;blob=subprocess.check_output(['git','show',git+':'+str(p.relative_to(R))],cwd=R);assert blob==b;checks.append({'path':str(p.relative_to(R)),'Git':git,'SHA256':H(b)})
assert checks[1]['SHA256']==h['stop_SHA256'];assert h['scientific_source_runtime_stopped'];assert h['scores']=={'input3':{'A':[1,1],'B':[0,0]},'input4':{'A':[0,0],'B':[0,0]}}
initial=json.loads((O/'input-before.json').read_text());unchanged=[]
for p,sha in initial['checks'].items():
 if ':' in p:continue
 if p.endswith('runtime-source-stopped-before-report.json'):continue
 assert H((R/p).read_bytes())==sha;unchanged.append({'path':p,'SHA256':sha})
(O/'final-input-binding.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_report_Git':g,'handoff_Git':hg,'checks':checks,'initial_stop_SHA256':initial['stop_SHA'],'final_stop_SHA256':h['stop_SHA256'],'distinct_stop_versions':True,'scientific_archive_required_inputs_unchanged':unchanged,'source_measurement_Gits':[x['source_Git'] for x in initial['source_and_stop']],'after_source_report_helpers_not_measurement_change':True,'owner_packed_Git_charge_failure_preserved':h['preservation_helper_failure'],'handoff_readonly_final_Git_not_new_science':True},indent=2)+'\n');print(json.dumps({'final_data_Git':g,'handoff_Git':hg,'handoffSHA':checks[0]['SHA256'],'final_stopSHA':h['stop_SHA256'],'necessary_Gitmatches':len(checks)}))
