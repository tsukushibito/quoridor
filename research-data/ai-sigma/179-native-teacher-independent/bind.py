import pathlib,json,hashlib,datetime,time,subprocess,os,resource
os.sched_setaffinity(0,{0});start=time.monotonic();D=pathlib.Path('research-data/ai-sigma/179-native-teacher-independent');A=pathlib.Path('research-data/ai-sigma/176-native-teacher-pipeline');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda n:json.loads((A/n).read_text());pr=load('learner-preregister.json');refs=[]
for n in ['preregister.json','openings.json','teacher-rows.jsonl.gz','all-game-status.json','dataset-summary.json','overlap-detail.json','learner-preregister.json','learner-training.json','learner-reload.json','learner-export.json','student-checkpoint.pt','student.onnx','arena-preregister.json','arena-results.json','cost-ledger.json','science-stop.json','binding.json','fixedK-parity.json','production-runs.json','gpu-root-parity-attempt1.json','gpu-root-parity.json','gpu-firstroot-final-join.json']:
 p=A/n;refs.append({'path':str(p),'bytes':p.stat().st_size,'SHA256':sha(p)})
sources=[]
for n in ['learn.py','worker.cjs','engine.cjs','schema.cjs','controller.cjs','arena.cjs','export.cjs']:
 p=pathlib.Path('tools/ai-sigma-native-teacher-pipeline')/n;actual=sha(p);expected=pr['source'].get(str(p));sources.append({'path':str(p),'SHA256':actual,'preregister_SHA256':expected,'match':actual==expected});assert actual==expected
for n in ['reference.cjs','game.js','context.js','reference-core-native.js','trace-reference.js']:
 p=pathlib.Path('tools/ai-sigma-native-baseline')/n;sources.append({'path':str(p),'SHA256':sha(p),'sharedRuleA':True})
p=load('fixedK-parity.json');par=[]
for index in [0,2]:
 a,b=p['rows'][index:index+2];assert a['slot']==b['slot'];assert a['cp']==b['cp'] and a['first_NN']==b['first_NN'];c=a['cp'];assert c['root_visits']==64 and sum(e[2]for e in c['root_edges'])==63;assert abs(c['root_mean']-c['root_valueSum']/64)<1e-14
 value=a['first_NN']['value'];assert abs(c['root_valueSum']-(value-sum(e[3]for e in c['root_edges'])))<1e-12
 par.append({'slot':a['slot'],'ply':a['ply'],'CP_counts':[a['CP_received'],b['CP_received']],'root_and_firstNN_equal':True,'backup_rootNN_minus_childvalue_sum_supported':True})
tr=load('learner-training.json');ex=load('learner-export.json');ar=load('arena-preregister.json');assert ar['student_SHA256']==ex['ONNX_SHA256'];loss={}
for split in ['train','validation']:
 before=tr['loss_before'][split];after=tr['loss_after'][split];assert all(after[k]<before[k]for k in [1,2]);loss[split]={'before_piCE':before[1],'after_piCE':after[1],'before_zMSE':before[2],'after_zMSE':after[2],'before_total':before[0],'after_total':after[0]}
stop=load('science-stop.json');identity=[]
for v in stop['all_owned_identity_checks']:
 pid=v.get('PID',v.get('pid'));p=pathlib.Path('/proc')/str(pid);identity.append({'PID':pid,'saved_start_ticks':v['start_ticks'],'current_absent':not p.exists()})
out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'HEAD_at_read':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'references':refs,'source':sources,'fixedK_finalOnly_finite':par,'loss_saved_untrained_baseline':loss,'saved_forward_confirmation_only':True,'NN_executed':0,'owner_stop_current_identities':identity,'allhost_allperiod_proof':False,'rootmean_all1409_backup_not_saved_fullledger':True,'GPU_version_scope':'originalr1/r2 + later NN0 firstroot join; futurerepair not included','elapsed_seconds':time.monotonic()-start,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024};(D/'binding.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['references','source','owner_stop_current_identities']}))
