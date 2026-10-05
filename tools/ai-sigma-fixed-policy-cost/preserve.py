import pathlib,json,hashlib,datetime,tarfile,resource,os,time
R=pathlib.Path(__file__).resolve().parents[2];T=R/'tools/ai-sigma-fixed-policy-cost';D=R/'research-data/ai-sigma/137-fixed-policy-cost';O=R/'.artifacts/ai-sigma/resume-20261002/FIXED-POLICY-COST';begin=time.time()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
s=load(D/'runtime-stopped-early.json');processes=[load(p) for p in (O/'runs').glob('*.process.json')];ids={}
for d in processes:
 assert not d['remaining'] and not d['unknown_adopted']
 for x in d['tracked']+[{'pid':d['runner_pid'],'start_ticks':d['runner_starttick']},{'pid':d['child_pid'],'start_ticks':d['child_starttick']}]:ids[(x['pid'],x['start_ticks'])]=x
same=[]
for pid,tick in ids:
 try:fields=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(fields[19])==tick:same.append({'pid':pid,'start_ticks':tick})
assert not same
rd=O/'runs/cost137-r2';mon=load(rd/'pause-monitor-stop.json');assert mon['all_owned_read_callbacks_waited'] and not mon['active_monitor_timer'] and not mon['pending_children']
source={str(p.relative_to(R)):sha(p) for p in T.iterdir() if p.is_file()};before=load(D/'source-before-r2.json');assert all(sha(R/p)==h for p,h in before.items())
bindings=load(rd/'source-bindings.json')
for v in bindings.values():assert sha(R/v['path'])==v['original_SHA256']
fixed={'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx':'d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d','.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm':'1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'}
for p,h in fixed.items():assert sha(R/p)==h
readonly=['tools/ai-sigma-actual-boundary-repair/reference-core.js','tools/ai-sigma-actual-boundary-repair/reference-control-run.js','tools/ai-sigma-actual-boundary-repair/host.js','tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-cp-frame/shared-best-action.cjs','tools/ai-sigma-player-workers/player-control.cjs','.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/ort.min.js']
fixed.update({p:sha(R/p) for p in readonly})
staticsecs=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in processes if x['phase']=='protocol')
s.update(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),identities=[{'pid':p,'start_ticks':t} for p,t in ids],identity_count=len(ids),current_same_identity=same,source_write_stopped=True,report_preparation_source_still_active=False,source_hashafter_all_own=source,necessary_readonly_current_hashes=fixed,served_adapted_hashes={k:v['adapted_SHA256'] for k,v in bindings.items()},monitored_static_seconds=staticsecs,unmanaged_short_management_fullperiod_PID_RSS_missing=True,closure_pack_short_process={'pid':os.getpid(),'start_ticks':int(pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),'excluded_from_managed_identity_union':True,'finishes_before_report_delivery':True},outer_ownedwait=[{'name':p['name'],'remaining':p['remaining'],'unknown':p['unknown_adopted'],'exit':p['exit'],'kernel_boundary':p['kernel_boundary']} for p in processes],not_natural_allperiod_allhost_proof=True)
save(D/'runtime-source-stopped-before-report.json',s)
files=[p for p in O.rglob('*') if p.is_file() and 'private-index' not in p.name and not any(a in ['t','xdg-cache','xdg-config'] for a in p.relative_to(O).parts)]
members=[{'path':str(p.relative_to(O)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)]
archive=D/'all-runs-failures.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for m in members:tar.add(O/m['path'],arcname=m['path'],recursive=False)
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==len(members)
 for m in members:
  b=tar.extractfile(m['path']).read();assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['SHA256']
save(D/'archive-manifest.json',{'issue':'quoridor-4lc.137','archive':str(archive.relative_to(R)),'SHA256':sha(archive),'bytes':archive.stat().st_size,'members':members,'all_member_restore_SHA_size':True,'models_shared_not_copied':True,'source_entry_Git':load(rd/'config.json')['Git']})
def alloc(folder):return sum(p.stat().st_blocks*512 for p in folder.rglob('*') if p.is_file())
current={str(p.relative_to(R)):alloc(p) for p in [T,O,D]};storage={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'current_allocated':current,'self_current':sum(current.values()),'valid_own_reservation':67108864,'valid_unused_before_Git':67108864-sum(current.values()),'Git_archive_transfer_forecast':8*1024*1024,'guard':58720256,'existing_experiment_entry_conservative':2147483648,'original134_current_Git_account_ref':'research-data/ai-sigma/134-local-move-quality/storage-final.json','old_unknown_not_decreased':True,'peak_not_added_current':True,'additional_parent_reservation':0,'allocation_valid_from137_contract_within_existing_entry':True,'private_index_peak_included_in_forecast':True,'closure_resource_self_maxrss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'closure_elapsed_seconds':time.time()-begin}
assert storage['self_current']+storage['Git_archive_transfer_forecast']<58720256
save(D/'storage-current.json',storage)
print(json.dumps({'archive_SHA':sha(archive),'members':len(members),'stop_SHA':sha(D/'runtime-source-stopped-before-report.json'),'identities':len(ids),'storage':storage,'staticsecs':staticsecs}))
