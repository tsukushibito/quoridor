"""Matched generation and cost comparison; no model/fit/old test reads."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,math,numpy as np,sys
R=Path.cwd();D=R/'research-data/ai-sigma/frame16-teacher-throughput'
O=D/'architecture-control'
def load(n):return json.loads(((O/n)if(O/n).exists()else(D/n)).read_text())
def rows(n):
 p=O/(n+'-teacher-rows.jsonl.gz');p=p if p.exists()else D/(n+'-teacher-rows.jsonl.gz')
 return [json.loads(s)for s in gzip.open(p,'rt')]
def costs(name):
 s=load(name+'-summary.json');out=(O/'jobs'/name)if(O/'jobs'/name).exists()else D/'jobs'/name;hist=s['batch']['batch_histogram'];calls=sum(hist);bmean=sum(i*n for i,n in enumerate(hist))/calls;starts=[];ends=[]
 for core in [2,4,6]:
  ss=[json.loads(l)for l in (out/f'core{core}/starts.jsonl').read_text().splitlines()];gg=[json.loads(l)for l in(out/f'core{core}/games.jsonl').read_text().splitlines()];start={x['game_id']:datetime.datetime.fromisoformat(x['UTC'].replace('Z','+00:00')).timestamp()for x in ss}
  starts.extend(start.values());ends.extend(start[g['game_id']]+g['elapsed_ms']/1000 for g in gg if 'elapsed_ms'in g)
 p=load('jobs/'+name+'/process.json');a=datetime.datetime.fromisoformat(p['startUTC']).timestamp();tail=sorted(ends)
 return dict(planned_games=48,qualified_joint=s['Rjoint'],jobwall_s=s['allattempt_jobwall_s'],joint_per_s=s['rates']['Rjoint'],completed_games=sum(s['status_counts'].get(k,0)for k in['GOAL','DRAW200','DRAW_NOLEGAL']),game_per_s=s['rates']['games'],actual_NN=s['actual_NN'],logical_NN=s['logical_worker_NN'],terminal_noNN=s['terminal_noNN'],discarded=s['discarded'],batch_calls=calls,actual_Bmean=bmean,Bhist=hist,provider_pipe_s=s['batch']['provider_pipe_ms']/1000,queue_sum_s=s['batch']['queue_ms_sum']/1000,queue_per_request_ms=s['batch']['queue_ms_sum']/s['actual_NN'],stages_s={k:v/1000 for k,v in s['providerCost']['stages'].items()},provider_JSON_firstpass_s=s['providerCost']['JSON_encode_firstpass_ms']/1000,provider_wire_totals_ms=s['providerStop'].get('wire_totals_ms'),provider_pipe=s['providerStop']['pipe'],worker_spans=[{k:c.get(k)for k in['raw_record_ms','search_ms','IPC_send_ms','bridge']}for c in s['worker_spans']],coldinit_until_first_game_s=min(starts)-a,last8_completion_tail_s=tail[-1]-tail[-8],game_generation_range_s=tail[-1]-min(starts),tail_clock_resolution_s=.001,tail_approximation='starts UTC plus game performance elapsed; 8 last completions, not exclusive provider tail',RSS_peak=s['sampled_peak_RSS'],VRAM_peak=s['providerStop']['GPU_peak_reserved_B'],status=s['status_counts'],overlap_spans_not_additive=True)
names=[n for n in['baseline','candidate','baseline-confirmation','graph-r1','graph-confirmation']if(D/(n+'-summary.json')).exists()or(O/(n+'-summary.json')).exists()];out={n:costs(n)for n in names};a=rows('baseline');b=rows('graph-r1');fa={r['game_id']:r for r in a if r['new_ply']==0};fb={r['game_id']:r for r in b if r['new_ply']==0};roots=[]
for g in sorted(fa.keys()&fb.keys()):
 x,y=fa[g],fb[g];assert x['features648_bits']==y['features648_bits'] and x['legal_order209']==y['legal_order209'] and sorted(x['history_counts'])==sorted(y['history_counts']) and x['family']==y['family'];nx=np.array(x['NN137_bits'],dtype=np.uint32).view(np.float32).astype(float);ny=np.array(y['NN137_bits'],dtype=np.uint32).view(np.float32).astype(float);roots.append(dict(game=g,feature_history_legal_bind=True,NNmaxabs=float(np.max(np.abs(nx-ny))),NNmaxtolratio=float(np.max(np.abs(nx-ny)/(1e-4+1e-4*np.abs(nx)))),rootmean_absdiff=abs(x['rootmean']-y['rootmean']),visit_vector_equal=x['visits136']==y['visits136'],action_equal=x['action209']==y['action209']))
assert len(roots)==48 and all(x['NNmaxtolratio']<=1 for x in roots)
# Full paired prefixes separate discrete branching from same-state finite numeric observations.
ba=collections.defaultdict(list);bb=collections.defaultdict(list)
for r in a:ba[r['game_id']].append(r)
for r in b:bb[r['game_id']].append(r)
prefix=[]
for g in fa:
 aa=sorted(ba[g],key=lambda x:x['new_ply']);bc=sorted(bb[g],key=lambda x:x['new_ply']);matched=0;firstbranch=None
 for x,y in zip(aa,bc):
  if x['state_key']!=y['state_key'] or sorted(x['history_counts'])!=sorted(y['history_counts']):break
  matched+=1
  if x['action209']!=y['action209']:firstbranch=x['new_ply'];break
 prefix.append(dict(game=g,baseline_rows=len(aa),candidate_rows=len(bc),same_state_prefix_rows=matched,first_action_divergence_ply=firstbranch))
base=out['baseline'];cand=out['graph-r1'];ratios=dict(jobwall_candidate_over_baseline=cand['jobwall_s']/base['jobwall_s'],joint_rate_candidate_over_baseline=cand['joint_per_s']/base['joint_per_s'],NN_candidate_over_baseline=cand['actual_NN']/base['actual_NN'],joint_rows_candidate_over_baseline=cand['qualified_joint']/base['qualified_joint'],game_rate_candidate_over_baseline=cand['game_per_s']/base['game_per_s']);attempts=[json.loads(p.read_text())for p in(O/'jobs').glob('*/process.json')];result=dict(issue='quoridor-4lc.221',conditions=out,ratios=ratios,roots=roots,paired_prefixes=prefix,allattempt=dict(wall_s=sum(x['jobwall_seconds']for x in attempts),NN=sum(x.get('sample_equivalent')or 0 for x in attempts),statuses=[{k:x.get(k)for k in['run','kind','exit','stop_reason','sample_equivalent','jobwall_seconds']}for x in attempts]),limits=dict(quality='RuleA/finite root and sample parity only, no deep teacher truth/strength',comparison='GPU24/B8 current baseline, not CPUJS',order='oldphase1B8/B24/B8 followedby graph/graph; sequential hostwarm and no newpairedB8 repetition; oldfailedwallUNKNOWN held5s',training_mix=False,fixed_conditions=True));(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'conditions':{k:{n:v[n]for n in['jobwall_s','qualified_joint','joint_per_s','actual_NN','actual_Bmean','last8_completion_tail_s','status']}for k,v in out.items()},'ratios':ratios,'root_visit_equal':sum(r['visit_vector_equal']for r in roots),'root_action_equal':sum(r['action_equal']for r in roots),'allattempt':result['allattempt']}))

more=[]
for name in ['graph-r1','graph-confirmation']:
 if not(O/(name+'-summary.json')).exists():continue
 other=rows(name);group={}
 for row in other:group[(row['game_id'],row['new_ply'])]=row
 numeric=[];actions=0;visits=0;same=0;maxNN=0.;maxmean=0.;maxratio=0.
 for x in a:
  y=group.get((x['game_id'],x['new_ply']))
  if not y or x['state_key']!=y['state_key']or sorted(x['history_counts'])!=sorted(y['history_counts']):continue
  same+=1;assert x['features648_bits']==y['features648_bits']and x['legal_order209']==y['legal_order209'];actions+=x['action209']==y['action209'];visits+=x['visits136']==y['visits136']
  nx=np.array(x['NN137_bits'],np.uint32).view(np.float32).astype(float);ny=np.array(y['NN137_bits'],np.uint32).view(np.float32).astype(float);maxNN=max(maxNN,float(np.max(np.abs(nx-ny))));maxratio=max(maxratio,float(np.max(np.abs(nx-ny)/(1e-4+1e-4*np.abs(nx)))));maxmean=max(maxmean,abs(x['rootmean']-y['rootmean']))
 assert maxratio<=1
 more.append(dict(name=name,baseline_rows=len(a),candidate_rows=len(other),same_state_history_rows=same,same_action_count=actions,same_visit_count=visits,rootNNmaxabs=maxNN,rootNNmaxtolratio=maxratio,rootmean_maxabs=maxmean,not_complete_deep_leaf_tape=True))
result['whole_qualified_row_correspondence']=more
result['phase1_NN']=243888;result['phase1_measuredwall']=350.917963652;result['phase1_failedwall']='UNKNOWN/conservative5s retained';result['phase2_NN']=sum(x['sample_equivalent']for x in attempts);result['totalNN']=243888+result['phase2_NN'];result['phase2_measuredwall']=sum(x['jobwall_seconds']for x in attempts)
if 'graph-confirmation'in out:
 bm=(out['baseline']['jobwall_s']+out['baseline-confirmation']['jobwall_s'])/2;gm=(out['graph-r1']['jobwall_s']+out['graph-confirmation']['jobwall_s'])/2
 result['mean_comparison']=dict(B8_baseline_meanwall=bm,graph_meanwall=gm,wallratio=gm/bm,jointrateratio=bm/gm,savedseconds_per_game=(bm-gm)/48)
(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(all_row_correspondence=more,totalNN=result['totalNN'],mean_comparison=result.get('mean_comparison'))))
