"""Necessary binding and stopped-identity check, without building or copying artifacts."""
import datetime,difflib,hashlib,json,pathlib,subprocess
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/153-sigma-web-port-saved-independent';Q=R/'research-data/ai-sigma/151-sigma-web-port';P=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs/port151-stageA-r2'
refs=[]
def hashfile(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def load(p):
 p=pathlib.Path(p);b=p.read_bytes();refs.append({'path':str(p.relative_to(R)),'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return json.loads(b)
def gitbytes(g,p):return subprocess.check_output(['git','show',g+':'+str(p)],cwd=R)
build=load(Q/'build-binding-r3.json');config=load(Q/'port151-stageA-r2-config.json');served=load(P/'actual-served-source.json');source=load(P/'source-bindings.json');dep=load(Q/'dependency-binding.json')
files=[]
for p,sha in build['source'].items():
 p=pathlib.Path(p);current=hashfile(p);g=gitbytes('b62cde0',p.relative_to(R));assert hashlib.sha256(g).hexdigest()==sha==current
 files.append({'path':str(p.relative_to(R)),'measured_Git':'b62cde0','SHA256':sha,'current_equal':True})
assert hashfile(pathlib.Path(served['/b.wasm']['path']))==config['binary_SHA256']==build['SHA256']==served['/b.wasm']['SHA256']
# Capture source-producing adapters only, with no worker, model load, or browser execution.
adapted_bundle=json.loads(subprocess.check_output(['node','--max-old-space-size=256','tools/ai-sigma-sigma-web-port-saved-independent/binding-scripts.cjs'],cwd=R))
adapted=adapted_bundle['measured']
routes={'/early-page.js':'main','/early-worker.js':'worker','/original-worker.js':'producer','/checkpoint.js':'checkpoint','/snapshot-cache.js':'cache','/reference-core.js':'reference','/player-base.js':'base-worker'}
for url,record in served.items():
 if url in routes:actual=adapted[routes[url]]['SHA256'];size=adapted[routes[url]]['bytes']
 elif url=='/numeric-browser.js':b=pathlib.Path(record['path']).read_bytes().replace(b'V.equal(ids,e[engine])',b'V.equal(ids,e.reference)');actual=hashlib.sha256(b).hexdigest();size=len(b)
 else:p=pathlib.Path(record['path']);actual=hashfile(p);size=p.stat().st_size
 assert actual==record['SHA256'] and size==record['bytes'],url
 files.append({'route':url,'source_path':record['path'],'SHA256':actual,'bytes':size,'adapted_route_not_original_path_bytes':url in routes,'measured_regenerated_equal':True,'current_adapted_equal':adapted_bundle['current'].get(routes.get(url),{}).get('SHA256')==record['SHA256'] if url in routes else True,'browser_independent_fetchdigest':None})
libraries=[]
patches={p['path']:p['diff'] for p in dep['uncommitted_current_library_diffs']}
for p,sha in dep['151_current_hashes'].items():
 q=R/p;assert hashfile(q)==sha
 patch=None
 if p in patches:
  try:before=gitbytes(dep['measured_Git'],p).decode()
  except subprocess.CalledProcessError:before=''
  patch=''.join(difflib.unified_diff(before.splitlines(keepends=True),q.read_text().splitlines(keepends=True)))
  assert patch==patches[p],p
 libraries.append({'path':p,'SHA256':sha,'current_mtime_UTC':datetime.datetime.fromtimestamp(q.stat().st_mtime,datetime.timezone.utc).isoformat(),'saved_patch_exact':patch is not None,'mtime_before_build':q.stat().st_mtime<datetime.datetime.fromisoformat(build['start']).timestamp()})
assert len(patches)==7
stop=load(Q/'port151-stageA-r2-stop.json');process=load(P.parent/'port151-stageA-r2.process.json');boot=(pathlib.Path('/proc/sys/kernel/random/boot_id')).read_text().strip();assert boot==process['kernel_boundary']['boot_id']
identities=[{'pid':p['pid'],'starttick':p['start_ticks']} for p in process['tracked']]+[{'pid':process['runner_pid'],'starttick':process['runner_starttick']}]
live=[];errors=[]
for ident in identities:
 try:
  now=pathlib.Path('/proc')/str(ident['pid'])/'stat';n=int(now.read_text().rsplit(')',1)[1].split()[19])
  if n==ident['starttick']:live.append(ident)
 except FileNotFoundError:pass
 except Exception as e:errors.append({'identity':ident,'error':str(e)})
assert not live and not errors
originalmonitor=R/'tools/ai-sigma-actual-boundary-repair/pause-check.cjs';old=gitbytes('b62cde0','tools/ai-sigma-sigma-web-port/diagnose.cjs').decode();new=(R/'tools/ai-sigma-sigma-web-port/diagnose.cjs').read_text()
assert "require('../ai-sigma-actual-boundary-repair/pause-check.cjs')" in old and "await monitor.stop();}catch" in old
assert "require('./pause-monitor.cjs')" in new and 'late_monitor_control_failure' in new
repair=(R/'tools/ai-sigma-sigma-web-port/pause-monitor.cjs').read_text();assert '> "$3"' in repair and 'bounded_schema_read_retry' in repair and 'all_owned_read_callbacks_waited' in repair
control={'measured_monitor':str(originalmonitor.relative_to(R)),'measured_monitor_SHA256':hashfile(originalmonitor),'measured_diagnose_SHA256':hashlib.sha256(old.encode()).hexdigest(),'current_diagnose_SHA256':hashlib.sha256(new.encode()).hexdigest(),'current_repair_private_reader':True,'bounded_retry_only':True,'late_failure_secondary_now_propagated':True,'current_repair_not_retroactive_r2_success':True,'monitor_fullperiod_success':False,'next_job_requires_fresh_ready_admission':True}
r1=P.parent/'port151-stageA-r1';r1hash=hashfile(r1/'browser-result.json');r1summary=load(r1/'summary.json');r1err=load(Q/'port151-stageA-r1-erratum.json')
startup=load(P/'startup.json');model=load(P/'model-load.json');assert startup['startup_NN']==6 and len(model['players'])==2
for player in model['players']:assert player['threads']==1 and not player['proxy'] and player['digest']==served['/model.onnx']['SHA256']
spans={'Model2drop':stop['files']['finally-model-drop'],'main_timer_message':stop['files']['main-timers-stop'],'monitorcallback':stop['files']['monitor-callback-stop'],'innercontrolled':stop['inner_controlled'],'outerwait':{'returned':stop['outer_ownedwait_returned'],'remaining':process['remaining'],'unknown':process['unknown_adopted']},'currentidentity':{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot':boot,'checked':len(identities),'remaining':live,'readerrors':errors},'source_launch_after_equal':stop['source_launch_hash']==stop['source_current_hash']}
out={'issue':'quoridor-4lc.153','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'r1_Git':'c706326','r1_raw_SHA256':r1hash,'r2_Git':'b62cde0','r2_binary_SHA256':build['SHA256'],'r2_build_start_end':[build['start'],build['end']],'latest_goal_design_Git_017681c_not_measurement_source':True,'necessary_files':files,'libraries9_patch7':libraries,'patch7_exact':True,'adapted_regeneration_refs':adapted_bundle['refs'],'partial_source_identity_not_full_build_read_audit':True,'served_records_are_server_not_browser_fetch':True,'control':control,'stop_boundaries':spans,'r2_handNN':320,'r2_startupNN':6,'owner_r1_r2_handNN_cumulative':r1summary['hand_NN']+320,'owner_StageA_NN_budget':1024,'owner_startup12_separate':True,'ORT_provider':'saved worker bridge CPU wasm, numThreads1/proxyfalse; no new provider inference','r1_erratum_reference':r1err,'refs':refs}
(D/'binding.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['necessary_files','libraries9_patch7','refs','r1_erratum_reference']}))
