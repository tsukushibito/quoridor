"""NN0 wholeattempt cost of new lineage; spans remain overlapping."""
from pathlib import Path
import json,datetime,collections
R=Path.cwd();O=R/'research-data/ai-sigma/frame16-teacher-throughput/fresh96-stage';name='fresh96-firstscience';J=O/'jobs'/name;s=json.loads((O/(name+'-summary.json')).read_text());p=json.loads((J/'process.json').read_text());start=datetime.datetime.fromisoformat(p['startUTC']).timestamp();starts={};end=[];events=[]
for c in[2,4,6]:
 for l in(J/f'core{c}/starts.jsonl').read_text().splitlines():
  x=json.loads(l);starts[x['game_id']]=datetime.datetime.fromisoformat(x['UTC'].replace('Z','+00:00')).timestamp()
 for l in(J/f'core{c}/games.jsonl').read_text().splitlines():
  x=json.loads(l)
  if x.get('elapsed_ms')is not None:
   t=starts[x['game_id']]+x['elapsed_ms']/1000;end.append(t);events.extend([(starts[x['game_id']],1),(t,-1)])
active=0;peak=0;timeline=[]
for t,v in sorted(events,key=lambda x:(x[0],x[1])):active+=v;peak=max(peak,active);timeline.append([t-start,active])
h=s['batch']['batch_histogram'];calls=sum(h);b=sum(i*n for i,n in enumerate(h))/calls;elapsed=s['allattempt_jobwall_s'];completed=sum(s['status_counts'].get(k,0)for k in['GOAL','DRAW200','DRAW_NOLEGAL']);attempts=[]
for pp in(O/'jobs').glob('*/process.json'):
 z=json.loads(pp.read_text());proof=pp.parent/'before-model-proof.json';a={k:z.get(k)for k in['run','jobwall_seconds','exit','stop_reason','sample_equivalent']}
 if proof.exists():a.update(before_model_science=False,confirmed_model_NN=0,original_null_sample_receipt_retained=True)
 attempts.append(a)
ends=sorted(end);x=dict(issue='quoridor-4lc.221',phase=4,new96_registered=True,conditions='fixed codecGraph24active/B8/K64/one real generation job',planned=96,started=len(starts),complete=completed,status=s['status_counts'],Rpolicy=s['Rpolicy'],Rz=s['Rz'],Rjoint=s['Rjoint'],unknown_z_rows=s['unknown_z_rows'],jobwall_s=elapsed,actual_NN_equivalent=s['actual_NN'],logical_NN=s['logical_worker_NN'],startup_graph_equivalent=108,terminal_noNN=s['terminal_noNN'],discard=s['discarded'],density_joint_per_registered_game=s['Rjoint']/96,density_joint_per_complete_game=s['Rjoint']/completed if completed else None,game_per_s=completed/elapsed,joint_per_s=s['Rjoint']/elapsed,actual_Bmean=b,fullB8_calls=h[8],partial_calls=sum(h[:8]),Bhist=h,cold_until_first_game_s=min(starts.values())-start,last8_completion_tail_s=ends[-1]-ends[-8]if len(ends)>=8 else None,last24_completion_tail_s=ends[-1]-ends[-24]if len(ends)>=24 else None,approx_active_peak=peak,approx_active_timeline=timeline,active_UTC_plus_elapsed_not_identity_count=True,worker_spans=s['worker_spans'],providerCost=s['providerCost'],providerStop=s['providerStop'],batch_stats=s['batch'],allattempt=attempts,allattempt_wall_s=sum(a['jobwall_seconds']for a in attempts),RSS_peak=p['peak_aggregate_RSS'],VRAM_allocator_reserved_B=s['providerStop']['GPU_peak_reserved_B'],VRAM_driver_instant_peak='UNKNOWN',overlap_spans_nonadditive=True,benchmark48_multiplier_not_pure_codec_cause='new lineage and prefix distributions/workload differ; private fresh sampler chooses class once per ply, old benchmark source calls RNG inside legal filter; old source/results not edited',training_mix=False,teacher_truth_or_K800_or_strength=False)
(O/'costs.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k]for k in ['planned','started','complete','status','Rjoint','unknown_z_rows','jobwall_s','actual_NN_equivalent','density_joint_per_registered_game','joint_per_s','actual_Bmean','last8_completion_tail_s','last24_completion_tail_s','allattempt_wall_s']}))
