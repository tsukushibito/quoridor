"""Post-run accounting only. Browser main remains the judge; no Node replay gate."""
import collections,datetime,hashlib,json,statistics,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX'
DATA=ROOT/'research-data/ai-sigma/119-diverse-prefix'
RUN=sys.argv[1]
rundir=OUT/'runs'/RUN
process=json.loads((OUT/'runs'/(RUN+'.process.json')).read_text())
assert not process['remaining'] and not process['unknown_adopted'],'RUN_OWNERSHIP_NOT_ZERO'
raw=json.loads((rundir/'browser-result.json').read_text()) if (rundir/'browser-result.json').exists() else json.loads((rundir/'partial-browser-result.json').read_text())
summary=json.loads((rundir/'summary.json').read_text())
rows=raw.get('rows',[]);games=raw.get('games',[])
def distribution(values):
 values=[x for x in values if x is not None]
 return {'n':len(values),'min':min(values) if values else None,'median':statistics.median(values) if values else None,'max':max(values) if values else None}
engines={}
for engine in ['candidate','reference']:
 selected=[r for r in rows if r['spec']['engine']==engine]
 cps=[r['diagnostic']['validated_cp'] for r in selected if (r.get('diagnostic') or {}).get('validated_cp')]
 first=[r['diagnostic']['sab_publications'][0]['validation_end_ms']-r['worker_clock']['mid_ms']-r['identity']['t0_ms'] for r in selected if (r.get('diagnostic') or {}).get('sab_publications')]
 engines[engine]={'public':len(selected),'classifications':dict(collections.Counter(r['response']['classification'] for r in selected)),
  'public_elapsed_ms':distribution(r['response']['public_elapsed_ms'] for r in selected),'first_completed_publication_ms':distribution(first),
  'ACK_wall_ms':distribution(r.get('ACK_wall_ms') for r in selected),'own_wait_ms':distribution(r.get('own_previous_wait',{}).get('wait_ms') for r in selected),
  'worker_stop_class':dict(collections.Counter(r.get('worker_stop_class','missing') for r in selected)),
  'hand_NN':sum(r.get('hand_NN',0) for r in selected),'post_public_new_NN_definite':sum(r.get('post_public_NN_definite',0) for r in selected),
  'NN_returned_after_public':sum(r.get('NN_returned_after_public',0) for r in selected),
  'retired_returns_discarded':sum(sum(bool(e.get('result_discarded')) for e in (r.get('diagnostic') or {}).get('NN_control_events',[])) for r in selected),
  'opposite_input_before_old_ACK':sum(bool(r.get('opposite_previous',{}).get('input_before_old_ACK')) for r in selected if r.get('opposite_previous')),
  'overlap_ACK_wall_ms':distribution(r['opposite_previous'].get('residual_overlap_wall_ms') for r in selected if r.get('opposite_previous')),
  'saved_completed_cp':len(cps),'cp_simulations':distribution(c.get('simulations') for c in cps),'cp_completed_NN':distribution(c.get('nn_calls') for c in cps),
  'candidate_max_depth':distribution(c.get('max_depth') for c in cps),'candidate_cap_true':sum(c.get('cap') is True for c in cps),
  'root_NN_rule':'candidate root-expanded backup included; edge visits=sim-1/rootNNvalue' if engine=='candidate' else 'Sigma root expansion outside sims; edge visits=sim/rootvisits=sim+1/rootQ'}
game_results=[];wdl=collections.Counter()
for g in games:
 status=g['status'];result='unfinished'
 if status in ['terminal','responsibility_loss']:
  result='D' if g['winner']==0 else 'W' if g['winner']==g['candidate_color'] else 'L'
 wdl[result]+=1
 game_results.append({k:g.get(k) for k in ['id','fixture_id','candidate_color','seed','status','winner','reason','responsible_engine','pair_invalid','total_ply'] }|{'candidate_result':result,'legal_actions_saved':len(g['actions']),'attempt_public':len(g['turn_indices'])})
end=json.loads((rundir/'clock-end.json').read_text()) if (rundir/'clock-end.json').exists() else {}
start=json.loads((rundir/'startup.json').read_text()).get('worker_clocks',{}) if (rundir/'startup.json').exists() else {}
clocks={e:{'start':start.get(e),'end':end.get(e),'offset_mid_change_ms':end[e]['mid_ms']-start[e]['mid_ms'] if e in start and e in end else None,'intermediate_drift_unobserved':True} for e in ['candidate','reference']}
s={'issue':'quoridor-4lc.119','run':RUN,'code_Git':summary['Git'],'games_started':raw.get('started_games',0),'games':game_results,'WDL':dict(wdl),'public':len(rows),'startup_NN':summary['startup_NN'],'hand_NN':summary['hand_NN'],
 'engines':engines,'fixed_gold_root_gates':sum(bool((r.get('gate') or {}).get('fixed_reference')) for r in rows),'dynamic_root_self_gates':sum(r.get('gate') is not None and not r['gate'].get('fixed_reference',False) for r in rows),
 'missing_eligible_public_cp':sum(bool((r.get('gate') or {}).get('missing_public_cp')) for r in rows),'postpublic_immutable_rows':sum(bool(r.get('postpublic_immutable')) for r in rows),
 'clock_calibration':clocks,'primary':summary['primary'],'secondary':summary['secondary'],'process':{'exit':process['exit'],'reason':process['stop_reason'],'RSS_peak':process['peak_group_plus_runner_RSS'],'storage_peak':process['peak_allocated_bytes'],'start':process['start'],'end':process['end'],'remaining':process['remaining'],'unknown':process['unknown_adopted']},
 'actual_go':False,'formal_fairness_NI':False,'CPU_API_and_ACK_not_kernel':True,'partial_tree_depth_missing_not_zero':True}
DATA.mkdir(exist_ok=True)
(DATA/(RUN+'.summary.json')).write_text(json.dumps(s,indent=2)+'\n')
files=sorted(p for p in rundir.rglob('*') if p.is_file())+sorted(p for p in (OUT/'runs').glob(RUN+'.*') if p.is_file())
archive=DATA/(RUN+'.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=4) as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(OUT)),recursive=False)
members=[]
with tarfile.open(archive,'r:gz') as tar:
 for member in tar.getmembers():
  rawbytes=tar.extractfile(member).read();p=OUT/member.name;assert hashlib.sha256(rawbytes).digest()==hashlib.sha256(p.read_bytes()).digest()
  members.append({'path':member.name,'bytes':len(rawbytes),'SHA256':hashlib.sha256(rawbytes).hexdigest()})
manifest={'issue':'quoridor-4lc.119','run':RUN,'source_Git':summary['Git'],'archive':archive.name,'SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'restore_root':str(OUT.relative_to(ROOT)),'stream_restore_checked':True,'members':members}
(DATA/(RUN+'.manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'run':RUN,'games':game_results,'WDL':dict(wdl),'public':len(rows),'NN':summary['hand_NN'],'archive_bytes':archive.stat().st_size,'primary':summary['primary'],'secondary':summary['secondary']}))
