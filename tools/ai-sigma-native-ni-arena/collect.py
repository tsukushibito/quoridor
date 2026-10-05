"""Post-stop owner aggregation. No NN, no changes to scientific files."""
import json, datetime, hashlib, subprocess, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
A=ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-NI-ARENA'
D=ROOT/'research-data/ai-sigma/173-native-ni-arena'
def read(p,default=None):
 return json.loads(p.read_text()) if p.exists() else default
def rows(p):
 return [json.loads(s) for s in p.read_text().splitlines() if s.strip()] if p.exists() else []
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def span(x):return (datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds()
def aggregate(epoch,run,manifest,force_unknown=False):
 out=A/'runs'/run;process=read(A/'runs'/(run+'.process.json'));assert process and not process['remaining'] and not process['unknown_adopted'],'NOT_STOPPED'
 result=read(out/'result.json',{});monitor=read(out/'pause-monitor.json',{});starts=rows(out/'block-starts.jsonl')
 raw={g['game_id']:g for core in (2,4,6) for g in rows(out/f'core{core}/games.jsonl')}
 journal=[x for core in (2,4,6) for x in rows(out/f'core{core}/journal.jsonl')]
 failure=monitor.get('failure');failed_block=starts[-1]['block'] if failure and starts else None
 slots=[];blocks=[];pair_rows=[];teachers=[]
 for b in manifest['blocks']:
  admitted=any(s['block']==b['block'] for s in starts);games=[]
  for spec in b['games']:
   g=raw.get(spec['game_id']);qualified=bool(g and g.get('quality_score') in (0,.5,1) and not force_unknown and b['block']!=failed_block)
   s={**spec,'epoch':epoch,'registered':admitted,'status':g['status'] if g else ('REGISTERED_UNKNOWN' if admitted else 'NOT_STARTED'),
      'qualification':'KNOWN' if qualified else 'UNKNOWN' if admitted else 'NONOBSERVED_CAPACITY',
      'quality_score':g['quality_score'] if qualified else None,'quality_interval':[g['quality_score']]*2 if qualified else [0,1],
      'raw_terminal_score':g.get('quality_score') if g else None,'raw_winner':g.get('winner') if g else None,
      'operational_score':g.get('operational_score') if g else None,
      'stop_reason':result.get('stop',process.get('stop_reason')),'control_failure':bool(force_unknown or b['block']==failed_block),
      'raw_game_path':str(out/f"core{spec['core']}/games.jsonl") if g else None}
   slots.append(s);games.append(s)
   if g and g.get('firstRoot'):
    root=g['firstRoot'];teachers.append({'game_id':g['game_id'],'pair':g['pair'],'epoch':epoch,'holdout':True,'training_use':False,
      'lineage_group':f"173-e{epoch}-pair-{g['pair']}",'source_root':root,'terminal_z_P1':None if g.get('winner') is None else (0 if g['winner']==0 else 1 if g['winner']==1 else -1),
      'terminal_z_side':None if g.get('winner') is None else (0 if g['winner']==0 else 1 if g['winner']==root['side'] else -1),
      'outcome_source':'raw terminal only; qualification separate','qualification':s['qualification']})
  if admitted:blocks.append({'block':b['block'],'results':[{'core':c,'games':[g for g in games if g['core']==c]}for c in (2,4,6)]})
  if admitted:
   for c in (2,4,6):
    gg=[g for g in games if g['core']==c];ss=[g['quality_score'] for g in gg];ww=[g['raw_winner'] for g in gg]
    pair_rows.append({'pair':gg[0]['pair'],'block':b['block'],'core':c,'Xi':sum(ss)/2 if all(x is not None for x in ss) else None,
      'quality_interval':[sum(g['quality_interval'][0] for g in gg)/2,sum(g['quality_interval'][1] for g in gg)/2],
      'same_board_side_winner':len(ww)==2 and ww[0] is not None and ww[0]==ww[1],
      'both_candidate_win':ss==[1,1],'both_candidate_loss':ss==[0,0],'raw_winners':ww})
 assert len(slots)==1200 and len({g['game_id']for g in slots})==1200
 save(D/f'epoch{epoch}-all-slots.json',slots);save(D/f'epoch{epoch}-processed-blocks.json',blocks);save(D/f'epoch{epoch}-pairs.json',pair_rows)
 save(D/f'epoch{epoch}-holdout-first-roots.json',teachers)
 cmd="const fs=require('fs'),s=require('./tools/ai-sigma-native-ni-arena/statistics.cjs');console.log(JSON.stringify(s.evaluate(JSON.parse(fs.readFileSync(process.argv[1])),JSON.parse(fs.readFileSync(process.argv[2])).statistics)));"
 stats=json.loads(subprocess.check_output(['node','-e',cmd,str(D/f'epoch{epoch}-processed-blocks.json'),str(D/('preregister-e2.json' if epoch==2 else 'preregister.json'))],cwd=ROOT))
 save(D/f'epoch{epoch}-inference.json',stats)
 # Separate Python integer arithmetic checks JS decisions on the retained scores.
 plus=[1]*5;minus=[1]*4;den=1;integer_check=[]
 for b,js in zip(blocks,stats['rows']):
  gg=[g for part in b['results']for g in part['games']]
  low=sum(int(2*g['quality_score'])for g in gg if g['quality_score'] is not None)
  high=low+sum(2 for g in gg if g['quality_score'] is None)
  plus=[v*(240+a*(5*low-27))for v,a in zip(plus,[1,2,4,6,8])]
  minus=[v*(240-a*(5*high-27))for v,a in zip(minus,[1,2,4,6])];den*=240
  assert str(sum(plus))==js['plus_numerator'] and str(5*den)==js['plus_denominator']
  assert str(sum(minus))==js['minus_numerator'] and str(4*den)==js['minus_denominator']
  assert (sum(plus)>=100*den)==js['NI_exact'] and (sum(minus)>=80*den)==js['inferiority_exact']
  integer_check.append({'block':b['block'],'k_low':low,'k_high':high,'JS_Python_exact_agree':True})
 save(D/f'epoch{epoch}-integer-check.json',{'rows':integer_check,'separate_arithmetic_shared_saved_scores':True,'new_NN':0})
 keys=['common_legal_preparation_ms','cleanup_after_public_ms','API_total_ms','pipe_total_ms','CP_received','CP_admitted','CP_late_discarded','CP_schema_rejected','NN_calls','NN_returned','NN_discarded','completed_K','terminal_noNN']
 totals={k:sum(x[k] for x in journal if isinstance(x.get(k),(int,float))) for k in keys}
 totals['overlapping_spans_not_added_to_wall']=True
 known=[g for g in slots if g['qualification']=='KNOWN'];term=[g for g in raw.values()if g.get('status') in ('GOAL','DRAW200','DRAW_NOLEGAL')]
 def dist(k):
  z=[x[k]for x in journal if isinstance(x.get(k),(int,float))];return {'count':len(z),'min':min(z)if z else None,'max':max(z)if z else None,'mean':sum(z)/len(z)if z else None}
 metrics={'epoch':epoch,'run':run,'registered_blocks':len(starts),'registered_games':len(starts)*6,'raw_terminal_games':len(term),
   'quality_known_games':len(known),'quality_unknown_registered_games':len(starts)*6-len(known),'future_unregistered_games':1200-len(starts)*6,
   'raw_statuses':dict(collections.Counter(g['status']for g in raw.values())),
   'known_WDL':{str(s):sum(g['quality_score']==s for g in known) for s in (1,.5,0)},
   'job_wall_seconds':span(process),'initialization_startup_NN':result.get('startup_NN'),'init':read(out/'init-all.json'),
   'terminal_games_per_job_second':len(term)/span(process),'qualified_games_per_job_second':len(known)/span(process),
   'qualified_first_root_rows':sum(t['qualification']=='KNOWN' for t in teachers),'qualified_first_root_rows_per_second':sum(t['qualification']=='KNOWN'for t in teachers)/span(process),
   'holdout_not_training_rows':True,'clock_and_cost_totals':totals,'clock_distributions':{k:dist(k) for k in ['firstCP_ms','public_actual_ms','cut_actual_ms','cleanup_after_public_ms','previous_zero_to_t0_ms']},
   'admit_end_max_ms':max((x['public_cp']['admit_ms'] for x in journal if x.get('public_cp')),default=None),
   'journal_requests':len(journal),'common_advance_ms':sum(x.get('advance_ms',0)for c in (2,4,6)for x in rows(out/f'core{c}/common-cost.jsonl')),
   'generation_wall_ms':sum(read(p)['wall_ms']for p in out.glob('generation-cost-*.json')),
   'peak_aggregate_RSS':process['peak_group_plus_runner_RSS'],'peak_allocated_bytes':process['peak_allocated_bytes'],
   'CPU_pool':process['allowed_compute_pool'],'kernelCPU_exact':None,'NN_API_await_not_kernelCPU':True,'stop':result.get('stop'),
   'outer_stop':process.get('stop_reason'),'primary':result.get('primary'),'remaining':process['remaining'],'unknown_owned':process['unknown_adopted'],
   'monitor_failure':failure,'monotonic_cross_process_epoch_guaranteed':False,'stationary_conditional_mean_verified':False,
   'process_sha256':hashlib.sha256((A/'runs'/(run+'.process.json')).read_bytes()).hexdigest()}
 save(D/f'epoch{epoch}-metrics.json',metrics);return metrics,stats
if __name__=='__main__':
 old=read(D/'openings.json');new=read(D/'openings-e2-seeds.json')
 m1,s1=aggregate(1,'native173-quality-r1',old,True)
 m2,s2=aggregate(2,'native173-quality-e2-r1',new)
 print(json.dumps({'epoch1_registered':m1['registered_games'],'epoch1_quality_unknown':m1['quality_unknown_registered_games'],'epoch2_registered':m2['registered_games'],'epoch2_known':m2['quality_known_games'],'epoch2_stop':m2['stop'],'epoch2_inference':s2['stop']}))
