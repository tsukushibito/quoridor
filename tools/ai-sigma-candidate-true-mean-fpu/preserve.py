from pathlib import Path
import json,hashlib,datetime,tarfile,os,resource,time
T=Path(__file__).parent;R=T.parents[1];D=R/'research-data/ai-sigma/140-candidate-true-mean-fpu';O=R/'.artifacts/ai-sigma/resume-20261002/CANDIDATE-TRUE-MEAN-FPU';begin=time.time()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
s=load(D/'runtime-stopped-early.json');same=[]
for v in s['identities']:
 try:st=Path(f"/proc/{v['pid']}/stat").read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(st[19])==v['start_ticks']:same.append(v)
assert not same
B=O/'runs/fpu140-mechanism-r1';monitor=load(B/'pause-monitor-stop.json');assert monitor['all_owned_read_callbacks_waited'] and not monitor['active_monitor_timer'] and not monitor['pending_children']
before=load(D/'source-before.json');assert all(sha(R/p)==h for p,h in before['own'].items());assert all(sha(R/p)==h for p,h in before['readonly'].items())
bindings=load(B/'source-bindings.json');bound={}
for k,v in bindings.items():
 if isinstance(v,dict) and 'path' in v:
  if 'original_SHA256' in v:assert sha(R/v['path'])==v['original_SHA256']
  bound[k]=v
source={str(p.relative_to(R)):sha(p) for p in T.rglob('*') if p.is_file()};served={v:sha(O/'build'/f'{v}.wasm') for v in ['q0','fpu']}
assert served==before['served']
s.update(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),current_same_identity=same,source_write_stopped=True,report_preparation_source_still_active=False,source_hashafter_all_own=source,necessary_readonly_current_hashes={p:sha(R/p) for p in before['readonly']},served_private_binary_hashafter=served,served_original_bindings=bound,closure_pack_short_process={'pid':os.getpid(),'start_ticks':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),'excluded_from_managed_identity_union':True,'ends_before_report_delivery':True},unmanaged_management_fullperiod_PID_RSS_affinity_missing=True)
save(D/'runtime-source-stopped-before-report.json',s)
# Required binaries, commands, all scientific rows/CPs, failures, clocks and ownership;
# no regenerable cached target or unused Chromium profile replication.
files=[]
for p in O.rglob('*'):
 if not p.is_file():continue
 parts=p.relative_to(O).parts
 if any(x in ['target-q0','target-fpu','t','xdg-cache','xdg-config'] for x in parts) or p.name.startswith('private-index'):continue
 files.append(p)
members=[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'SHA256':sha(p)} for p in sorted(files)]
a=D/'all-runs-failures.tar.gz'
with tarfile.open(a,'w:gz') as tar:
 for m in members:tar.add(O/m['path'],arcname=m['path'],recursive=False)
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==len(members)
 for m in members:
  b=tar.extractfile(m['path']).read();assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['SHA256']
save(D/'archive-manifest.json',{'issue':'quoridor-4lc.140','archive':str(a.relative_to(R)),'SHA256':sha(a),'bytes':a.stat().st_size,'members':members,'all_member_restore_SHA_size':True,'source_Git':load(D/'analysis.json')['measured_Git'],'shared_model_ORT_original_Wasm_not_copied':True,'cached_targets_excluded_as_regenerable':True,'restoration_destination':'selfOUT or independent configured root; originalshared paths readonly'})
current={str(p.relative_to(R)):sum(q.stat().st_blocks*512 for q in p.rglob('*') if q.is_file()) for p in [T,O,D]};forecast=8*1024**2
assert sum(current.values())+forecast<234881024
save(D/'storage-current.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'current_allocated':current,'self_current':sum(current.values()),'forecast_Git_archive_index':forecast,'guard':234881024,'valid_self_reservation':268435456,'valid_unused_beforeGit':268435456-sum(current.values()),'existing_experiment_entry_conservative':2147483648,'old_unknown_not_decreased':True,'additional_parent_reservation':0,'peak_not_added_current':True,'build_targets_in_current_until_owned_stop_Git_restore':True,'preserve_self_peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'preserve_wall_seconds':time.time()-begin})
print(json.dumps({'stop_SHA':sha(D/'runtime-source-stopped-before-report.json'),'archive_SHA':sha(a),'members':len(members),'current_bytes':sum(current.values())}))
