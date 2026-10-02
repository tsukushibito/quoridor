import json,hashlib,datetime,os,tarfile,io,subprocess
from pathlib import Path
R=Path.cwd();T=R/'tools/ai-sigma-player-workers-independent';O=R/'.artifacts/ai-sigma/resume-20261002/PLAYER-WORKERS-INDEPENDENT';D=R/'research-data/ai-sigma/113-player-workers-independent';D.mkdir(exist_ok=True)
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text());b=read(O/'input-before.json');after={p:hashfile(Path(p)) for p in b['source']};assert all(h==b['source'][p]['actual'] for p,h in after.items())
process=[];ident={}
for p in sorted((O/'runs').glob('*.process.json')):
 j=read(p);assert not j['remaining'] and not j['unknown_adopted'];process.append({k:j[k] for k in ['name','start','end','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','kernel_adoptions','all_observed_TIDs_at_assigned_CPU']})
 for x in j['tracked']:ident[(x['pid'],x['start_ticks'])]={'pid':x['pid'],'starttick':x['start_ticks']}
 for role in ['runner','child']:ident[(j[role+'_pid'],j[role+'_starttick'])]={'pid':j[role+'_pid'],'starttick':j[role+'_starttick']}
live=[]
for x in ident.values():
 try:
  if int(Path(f"/proc/{x['pid']}/stat").read_text().split(') ')[1].split()[19])==x['starttick']:live.append(x)
 except FileNotFoundError:pass
assert not live
run=O/'runs/p113-functional-r2';runtime=read(run/'independent-runtime.json');saved=read(run/'independent-saved.json');summary=read(run/'summary.json');drops=read(run/'finally-model-drop.json');timer=read(run/'main-timers-stop.json');monitor=read(run/'pause-monitor-stop.json');outer=read(run/'outer-controlled-stop.json');assert drops['handles']==0 and drops['activeNN']==0 and timer['main_timers']==0 and not timer['pending_messages'] and not monitor['pending_children']
stop={'issue':'quoridor-4lc.113','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_runtime_stopped':True,'processes':process,'identity_count':len(ident),'identity_union':list(ident.values()),'current_same_identity_live':live,'Modeldrop':drops,'main_timers':timer,'monitor_state':monitor['state'],'monitor_pending_children':monitor['pending_children'],'outer_remaining':outer['remaining_pids'],'inner_controlled':outer.get('controlled_stop'),'forced_not_natural':True,'source_after':after,'self_source':{str(p):hashfile(p) for p in T.iterdir() if p.is_file()},'new_NN_game_after_stop':0,'actual_go':False,'current_absence_not_all_period':True}
(O/'runtime-source-stopped-before-report.json').write_text(json.dumps(stop,indent=2)+'\n');(O/'input-after.json').write_text(json.dumps(after,indent=2)+'\n')
compact={'issue':'quoridor-4lc.113','producer_Git':'3682ab7b520024735e79e42eea79c982897c3957','saved':[{'run':x['run'],'counts':x['counts']} for x in saved['runs']],'saved_games':saved['games'],'saved_WDL':{'W':saved['W'],'D':0,'L':saved['L']},'saved_numeric_samples':saved['numeric_samples'],'runtime':runtime,'runtime_summary':summary,'startup_NN':summary['startup_NN'],'primary_failed_NN0_configuration':read(O/'configuration-failure-r1.json'),'processes':process,'identity_count':len(ident),'snapshot_public_immutable':True,'API_await_not_kernel_CPU':True,'single_logical_shared_residual_contention_not_measured':True,'same_RuleA_independence_limit':True,'no_game_holdout_build':True,'stop_SHA':hashfile(O/'runtime-source-stopped-before-report.json')}
(O/'independent-summary.json').write_text(json.dumps(compact,indent=2)+'\n')
for n in ['independent-summary.json','runtime-source-stopped-before-report.json','preregister.json','input-before.json','input-after.json','headroom-before.json']:(D/n).write_bytes((O/n).read_bytes())
# All owned required run evidence is small; exclude live aliases/cache, own index and dispatch prose.
files=[p for p in O.rglob('*') if p.is_file() and not any(part in ['t','xdg-cache','xdg-config'] for part in p.relative_to(O).parts) and p.name not in ['research.index','start-report.txt'] and p.suffix not in ['.lock']]
archive=D/'run-evidence.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as tf:
 for p in sorted(files):tf.add(p,arcname=str(p.relative_to(O)),recursive=False)
entries=[]
with tarfile.open(archive,'r:gz') as tf:
 for p in sorted(files):data=tf.extractfile(str(p.relative_to(O))).read();assert data==p.read_bytes();entries.append({'path':str(p.relative_to(O)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(D/'archive-manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.113','archive_sha256':hashfile(archive),'archive_bytes':archive.stat().st_size,'entries':entries,'all_match':True,'original_reference_only':'research-data/ai-sigma/112-player-workers/run-evidence.tar.gz','stop_SHA':compact['stop_SHA']},indent=2)+'\n');print(json.dumps({'stopSHA':compact['stop_SHA'],'identities':len(ident),'heavy_end':process[-1]['end'],'archivebytes':archive.stat().st_size,'members':len(entries)}))
