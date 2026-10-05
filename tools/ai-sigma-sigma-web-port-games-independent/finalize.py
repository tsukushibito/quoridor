import pathlib,json,hashlib,subprocess,os,datetime
R=pathlib.Path.cwd();T=R/'tools/ai-sigma-sigma-web-port-games-independent';D=R/'research-data/ai-sigma/155-sigma-web-port-games-independent';report=R/'docs/reports/ai-sigma-critic-sigma-web-port-games-independent.md'
def sha(b):return hashlib.sha256(b).hexdigest()
checks=[];identities=set()
for f in D.glob('*.process.json'):
 d=json.loads(f.read_text());assert d['child_waited'] and not d['remaining'];checks.append(d)
 for x in d['owned']:identities.add((x['pid'],x['starttick']))
same=[]
for pid,tick in identities:
 try:a=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(a[19])==tick:same.append({'pid':pid,'starttick':tick})
assert same==[]
source={str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.suffix in ['.cjs','.py']};source[str(report.relative_to(R))]=sha(report.read_bytes())
scope=[p for root in [T,D] for p in root.rglob('*') if p.is_file() and not p.name.startswith('private.index')]+[report];allocated=sum(p.stat().st_blocks*512 for p in scope);ad=json.loads((D/'storage-admission.json').read_text());assert allocated<6*1024**2 and ad['prior_conservative_bytes']+ad['153_current_allocated']+allocated<ad['guard']
stop={'issue':'quoridor-4lc.155','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'science_and_checker_source_stopped':True,'checker_children_waited':True,'checker_current_sameidentity':same,'identity_count':len(identities),'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'currentabsence_not_natural_fullperiod_allhost':True,'source_SHA256':source,'checker_attempts':[{'run':x['run'],'exit':x['exit'],'wall_s':x['wall_s']}for x in checks],'checker_child_wall_sum':sum(x['wall_s'] for x in checks),'observed_currentRSS_peak':max(x['peak_observed_current_RSS']for x in checks),'administration_and_team_full_cost_unknown':True,'newscope_allocated_before_Git_index':allocated,'critic_prior_conservative':ad['prior_conservative_bytes']+ad['153_current_allocated'],'forecast_remaining_own_Git_manifest_bytes':262144,'unknown_old_discount':0,'NN_Chrome_model_game_build':0,'Git_backup_helpers_pending':True}
(D/'source-process-stop.json').write_text(json.dumps(stop,indent=2))
env={**os.environ,'GIT_INDEX_FILE':str(T/'private.index')}
subprocess.run(['git','read-tree','HEAD'],env=env,check=True)
paths=['tools/ai-sigma-sigma-web-port-games-independent','research-data/ai-sigma/155-sigma-web-port-games-independent','docs/reports/ai-sigma-critic-sigma-web-port-games-independent.md']
subprocess.run(['git','rm','--cached','--ignore-unmatch','--',str((T/'private.index').relative_to(R)),str((T/'private.index.lock').relative_to(R))],env=env,check=True)
subprocess.run(['git','add','--',*paths,':!tools/ai-sigma-sigma-web-port-games-independent/private.index',':!tools/ai-sigma-sigma-web-port-games-independent/private.index.lock'],env=env,check=True)
subprocess.run(['git','commit','-m','research(155): independently verify saved Sigma port games'],env=env,check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();manifest=[]
for p in scope+[D/'source-process-stop.json']:
 if p.name=='private.index' or p.name.startswith('finalize-'):continue
 rel=str(p.relative_to(R));b=subprocess.check_output(['git','show',commit+':'+rel]);assert b==p.read_bytes();manifest.append({'path':rel,'bytes':len(b),'SHA256':sha(b),'Gitblob_matches_current':True})
(D/'Git-stream-restore.json').write_text(json.dumps({'Git':commit,'canonical':manifest,'count':len(manifest),'no_fullcopy_extract':True},indent=2));print(json.dumps({'Git':commit,'restore_count':len(manifest),'source_stop_SHA256':sha((D/'source-process-stop.json').read_bytes())}))
