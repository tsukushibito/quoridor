"""NN0 all-attempt/qualified-root comparison; overlapping spans are nonadditive."""
from pathlib import Path
import json,datetime,collections,gzip,math,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-worker-balance';start=time.monotonic()
load=lambda p:json.loads(p.read_text())
def lines(p):
 if p.exists():
  for l in p.read_text().splitlines():
   if l.strip():yield json.loads(l)
def costs(name):
 J=D/'jobs'/name;s=load(D/(name+'-summary.json'));p=load(J/'process.json');starts={};ends=[]
 for core in[2,4,6]:
  for x in lines(J/f'core{core}/starts.jsonl'):starts[x['game_id']]=datetime.datetime.fromisoformat(x['UTC'].replace('Z','+00:00')).timestamp()
  for x in lines(J/f'core{core}/games.jsonl'):
   if x.get('elapsed_ms')is not None:ends.append(starts[x['game_id']]+x['elapsed_ms']/1000)
 ends.sort();h=s['batch']['batch_histogram'];calls=sum(h);done=sum(s['status_counts'].get(k,0)for k in['GOAL','DRAW200','DRAW_NOLEGAL']);wall=s['allattempt_jobwall_s']
 x=dict(name=name,planned=96,complete=done,status=s['status_counts'],Rpolicy=s['Rpolicy'],Rz=s['Rz'],Rjoint=s['Rjoint'],unknown_z_rows=s['unknown_z_rows'],zero_eligible_games=[x['id']for x in s['all_slot_plies']if x['new_rows']==0],jobwall_s=wall,qualification_s=s['qualify_wall_s'],game_per_s=done/wall,joint_per_s=s['Rjoint']/wall,NN_equivalent=s['actual_NN'],logical_NN=s['logical_worker_NN'],startup=s['actual_NN']-s['logical_worker_NN'],terminal_noNN=s['terminal_noNN'],Bmean=sum(i*n for i,n in enumerate(h))/calls,Bhist=h,fullB8=h[8],partial=sum(h[:8]),tail8_s=ends[-1]-ends[-8]if len(ends)>=8 else None,tail24_s=ends[-1]-ends[-24]if len(ends)>=24 else None,tail_clock_mixed_UTC_plus_elapsed_approximate=True,worker_spans=s['worker_spans'],RSS_peak=p['peak_aggregate_RSS'],VRAM_allocator_peak=s['providerStop']['GPU_peak_reserved_B'],VRAM_driver_instant_peak='UNKNOWN',providerCost=s['providerCost'],pipe=s['providerStop']['pipe'],batch_stats=s['batch'],overlap_spans_nonadditive=True,all_slot_plies=s['all_slot_plies'],job_only_1000_min=1000*wall/done/60 if done else None,job_plus_qualification_1000_min=1000*(wall+s['qualify_wall_s'])/done/60 if done else None,production1000_NOT_RUN=True,benchmark_siblings_no_training_mix=True)
 (D/(name+'-costs.json')).write_text(json.dumps(x,indent=2)+'\n');return x
names=[n for n in['baseline-r3','balanced-r3']if(D/(n+'-summary.json')).exists()];out={'issue':'quoridor-4lc.225','conditions':[costs(n)for n in names]}
attempt=[]
for pp in(D/'jobs').glob('*/process.json'):
 p=load(pp);x={k:p.get(k)for k in['run','jobwall_seconds','exit','stop_reason','sample_equivalent','all_child_waited','current_exact_absent']}
 proof=pp.parent/'before-model-proof.json'
 if proof.exists():x['finite_before_import_source_proof']=load(proof);x['ledger_NN_equivalent']=0
 else:
  x['ledger_NN_equivalent']=p['sample_equivalent'] if p['sample_equivalent'] is not None else p['NN_cap']
  x['NN_upper_charged_not_observed']=p['sample_equivalent'] is None
 attempt.append(x)
out['all_attempts']=attempt;out['all_attempt_jobwall_s']=sum(x['jobwall_seconds']for x in attempt);out['total_NN_equivalent']=sum(x['ledger_NN_equivalent']for x in attempt if x['ledger_NN_equivalent']is not None)
if len(names)==2:
 a,b=out['conditions'];out['candidate_minus_baseline_wall_s']=b['jobwall_s']-a['jobwall_s'];out['candidate_wall_reduction_fraction']=1-b['jobwall_s']/a['jobwall_s'];out['Rjoint_rate_ratio']=b['joint_per_s']/a['joint_per_s'];out['same_work']={k:a[k]==b[k]for k in['complete','Rjoint','logical_NN','terminal_noNN']}
 def raw(name):
  return {(x['game_id'],x['new_ply']):x for core in[2,4,6]for x in lines(D/'jobs'/name/f'core{core}/raw-rows.jsonl')}
 aa,bb=raw(names[0]),raw(names[1]);pairs=set(aa)&set(bb);fields=['state_key','history_counts','features648_bits','legal_order209','mapping136','visits136','action209','rootN','edgeSum'];mismatch=collections.Counter();numeric={'rootNN':0.,'rootmean':0.,'leafNN':0.};bitrows=0
 for k in pairs:
  x,y=aa[k],bb[k]
  for f in fields:
   if x[f]!=y[f]:mismatch[f]+=1
  bitrows+=x['NN137_bits']!=y['NN137_bits']
  if x['state_key']==y['state_key']:
   for f in numeric:
    if isinstance(x[f],(float,int))and isinstance(y[f],(float,int)):numeric[f]=max(numeric[f],abs(x[f]-y[f]))
 out['finite_all_root_comparison']={'baseline_rows':len(aa),'candidate_rows':len(bb),'paired':len(pairs),'missing_baseline':len(set(bb)-set(aa)),'missing_candidate':len(set(aa)-set(bb)),'mismatch':dict(mismatch),'NN137_bits_differ_rows':bitrows,'same_state_numeric_maxabs':numeric,'leaf_truth_not_certified':True}
 out['third_baseline_status']='baseline-r3 wholework verification; censored-first-baseline retained, no successful replacement';out['order_hostwarm_not_bracketed']=True;out['comparison_order']='censored baseline-r2 -> balanced-r3 -> baseline-r3; first full baseline unavailable'
 out['break_even_independent_games']={'known_science_increment_cost_s':out['all_attempt_jobwall_s'],'seconds_saved_per96':a['jobwall_s']-b['jobwall_s'],'unknown_development_export_pack_git_backup_s':'UNKNOWN','definition':'N=C/(delta per game), development and qualification costs separate; no finite claim when delta<=0'}
out['analysis_s']=time.monotonic()-start;(D/'comparison.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in['conditions','all_attempts']},indent=2))
