import json,statistics
from pathlib import Path
D=Path(__file__).resolve().parents[2]/'research-data/ai-sigma/180-native-k800-time';A=D.parents[2]/'.artifacts/ai-sigma/resume-20261003/NATIVE-K800-TIME';job=A/'runs/native180-measure-r1'
rows=[json.loads(s)for s in (job/'rows.jsonl').read_text().splitlines()];status=json.loads((job/'status.json').read_text());groups=[]
for fixture in ['initial-p1','asym-hv-p2','straight-jump-p2']:
 rr=[x for x in rows if x['fixture']==fixture];engines={}
 for name in ['candidate','reference']:
  steady=[x for x in rr if x['engine']==name and x['phase']=='steady'];times=[x['elapsed_ms']for x in steady]
  engines[name]={'steady_n':len(times),'median_ms':statistics.median(times)if times else None,'min_ms':min(times)if times else None,'max_ms':max(times)if times else None,'steady_times_ms':times,'warm_ms':[x['elapsed_ms']for x in rr if x['engine']==name and x['phase']=='warm'],'NN_actual':[x['NN_actual']for x in steady],'terminal_noNN':[x['terminal_noNN']for x in steady],'NN_API_sum_ms':[x['NN_API_sum_ms']for x in steady],'NN_pipe_sum_ms':[x['NN_pipe_sum_ms']for x in steady],'bridge':[x['bridge']for x in steady]}
 checks=[];base=next((x for x in rr if x['engine']=='reference'),None)
 for x in rr:
  if base is None:continue
  ce,be=x['cp']['root_edges'],base['cp']['root_edges'];order=[e[0]for e in ce]==[e[0]for e in be];discrete=order and [e[2]for e in ce]==[e[2]for e in be] and x['cp']['action']==base['cp']['action']
  checks.append({'slot':x['slot'],'rootNN_bits_exact':x['first_NN']['NN_bits']==base['first_NN']['NN_bits'],'features_bits_exact':x['first_NN']['features_bits']==base['first_NN']['features_bits'],'root_state_exact':x['root_state']==base['root_state'],'root_action_visits_exact':discrete,'root_legal_order_exact':order,'root_mean_absdiff':abs(x['cp']['root_mean']-base['cp']['root_mean']),'root_edge_numeric_max_absdiff':max((abs(a[i]-b[i])for a,b in zip(ce,be)for i in [1,3]),default=0)if order else None})
 steady=[x for x in rr if x['phase']=='steady'];paired=[]
 for i in range(0,len(steady)-1,2):
  pair=steady[i:i+2];c=next(x for x in pair if x['engine']=='candidate');r=next(x for x in pair if x['engine']=='reference');paired.append(c['elapsed_ms']/r['elapsed_ms'])
 groups.append({'fixture':fixture,'engine':engines,'C_over_R_median_ratio':engines['candidate']['median_ms']/engines['reference']['median_ms']if engines['reference']['median_ms']else None,'paired_C_over_R':paired,'finite_correspondence':checks})
stop=json.loads((job/'stop.json').read_text());process=json.loads((A/'runs/native180-measure-r1.process.json').read_text());init=json.loads((job/'init.json').read_text());result={'issue':'quoridor-4lc.180','groups':groups,'all30status':status,'searches_completed':len(rows),'NN_actual':sum(x['NN_actual']for x in rows),'terminal_noNN':sum(x['terminal_noNN']for x in rows),'discarded':sum(x['discarded']for x in rows),'cache_hits':sum(x['cache_hits']for x in rows),'startup_actual':sum(x['init']['startup']['count']for x in init),'initializations':init,'stop':stop,'process_summary':{k:process[k]for k in ['start','end','exit','stop_reason','peak_group_plus_runner_RSS','remaining','unknown_adopted','all_observed_TIDs_at_assigned_CPU','affinity_violations']},'unknown_costs':['exclusive feature/legal/BFS cost','exclusive MCTS CPU','exclusive parse/record cost','instrumentation-free counterfactual','kernelCPU attribution'],'interpretation':'sameK800 finite native-hosted fixedWeb JS vs faithful Rust via current JSON bridge; no C++/Wasm/NI/fullteacher-speed extrapolation'}
(D/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'completed':len(rows),'NN':result['NN_actual'],'groups':[{k:x[k]for k in ['fixture','C_over_R_median_ratio','paired_C_over_R']}for x in groups]}))
