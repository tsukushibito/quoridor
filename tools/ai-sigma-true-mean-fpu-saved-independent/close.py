import datetime,hashlib,json,pathlib,tarfile
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/141-true-mean-fpu-saved-independent';O=R/'.artifacts/ai-sigma/resume-20261002/TRUE-MEAN-FPU-SAVED-INDEPENDENT';T=pathlib.Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
runs=[json.loads(p.read_text()) for p in sorted(O.glob('*.process.json'))];identities={(i['pid'],i['start_ticks']):i for r in runs for i in r['owned']};current=[];errors=[]
for (pid,tick),i in identities.items():
 try:s=pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 except Exception as e:errors.append(str(e));continue
 if int(s[19])==tick:current.append(i)
assert not current and not errors
f=json.loads((D/'failures.json').read_text());f['checker_run_failures']=[{'run':'check-r1','exception':'IndexError interim CP tree empty; retain log/hashbefore; recover edge state from complete selection/visit ledger, final priors','scientific_negative':False}];f['checker_format_corrections']=[{'run':'check-r2','failed_checks':7,'cause':'difflib patch header named paths but stored headers blank; content/current hashes unchanged','scientific_negative':False},{'run':'check-r3','failed_checks':0},{'run':'check-r4','failed_checks':0,'added':'saved startup/session/model and CP finish convention'}];dump(D/'failures.json',f)
stop={'issue':'quoridor-4lc.141','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_write_stopped':True,'Chrome_NN_Wasm_build_model_game':0,'own_source_hashafter':{str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()},'managed_runs':runs,'owned_observed_identity_count':len(identities),'current_same_identity':current,'read_errors':errors,'remaining_unknown_observed':False,'current_absence_not_natural_fullperiod_allhost':True,'short_child_between_samples_missing':True,'managed_wall_s':sum(r['wall_s'] for r in runs),'max_observed_RSS':max(r['peak_observed_RSS'] for r in runs),'CPU':[0],'each_command_60_s':all(r['wall_s']<60 for r in runs),'managed_180_s':sum(r['wall_s'] for r in runs)<180,'RAM_guard':448*1024**2,'readonly_short_intake_commands_outside_managed_clock':True}
dump(D/'runtime-source-stopped-before-report.json',stop)
members=[p for p in O.iterdir() if p.is_file() and (p.suffix in ['.log','.json'])];arc=D/'own-attempts.tar.gz'
with tarfile.open(arc,'w:gz') as a:
 for p in members:a.add(p,arcname=p.name,recursive=False)
entries=[]
with tarfile.open(arc) as a:
 for m in a.getmembers():
  b=a.extractfile(m).read();assert b==(O/m.name).read_bytes();entries.append({'path':m.name,'bytes':len(b),'SHA256':sha(b)})
dump(D/'archive-manifest.json',{'issue':'quoridor-4lc.141','archive':str(arc.relative_to(R)),'SHA256':sha(arc.read_bytes()),'bytes':arc.stat().st_size,'members':entries,'restore':str(O.relative_to(R)),'all_member_stream_restore_equal':True,'original_140_archive_not_copied':True})
print(json.dumps({'stop':{k:v for k,v in stop.items() if k not in ['managed_runs','own_source_hashafter']},'archive_members':len(entries),'archive_bytes':arc.stat().st_size}))
