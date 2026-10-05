from pathlib import Path
T=Path('tools/ai-sigma-teacher-throughput');A=T/'architecture-control'
s=(T/'compare.py').read_text();s=s.replace("def load(n):return json.loads((D/n).read_text())", "O=D/'architecture-control'\ndef load(n):return json.loads(((O/n)if(O/n).exists()else(D/n)).read_text())")
s=s.replace("def rows(n):return [json.loads(s)for s in gzip.open(D/(n+'-teacher-rows.jsonl.gz'),'rt')]", "def rows(n):\n p=O/(n+'-teacher-rows.jsonl.gz');p=p if p.exists()else D/(n+'-teacher-rows.jsonl.gz')\n return [json.loads(s)for s in gzip.open(p,'rt')]")
s=s.replace("out=D/'jobs'/name;hist", "out=(O/'jobs'/name)if(O/'jobs'/name).exists()else D/'jobs'/name;hist")
s=s.replace("['baseline','candidate','baseline-confirmation']if(D/(n+'-summary.json')).exists()", "['baseline','candidate','baseline-confirmation','graph-r1','graph-confirmation']if(D/(n+'-summary.json')).exists()or(O/(n+'-summary.json')).exists()")
s=s.replace("b=rows('candidate')","b=rows('graph-r1')").replace("cand=out['candidate']","cand=out['graph-r1']")
s=s.replace("attempts=[json.loads(p.read_text())for p in(D/'jobs').glob('*/process.json')]", "attempts=[json.loads(p.read_text())for p in(O/'jobs').glob('*/process.json')]")
s=s.replace("(D/'comparison.json')", "(O/'comparison.json')")
s=s.replace("order='baseline then candidate; optional baseline confirmation'", "order='oldphase1B8/B24/B8 followedby graph/graph; sequential hostwarm and no newpairedB8 repetition; oldfailedwallUNKNOWN held5s'")
s=s.replace("print(json.dumps({'conditions'", "print(json.dumps({'conditions'")
# Additional same-state finite observations across all qualified teacher roots, discrete comparisons separate.
s+='''\nmore=[]
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
(O/'comparison.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(dict(all_row_correspondence=more,totalNN=result['totalNN'],mean_comparison=result.get('mean_comparison'))))
'''
(A/'compare.py').write_text(s)
s=(T/'pack.py').read_text().replace("D=R/'research-data/ai-sigma/frame16-teacher-throughput'","D=R/'research-data/ai-sigma/frame16-teacher-throughput/architecture-control'").replace('benchmark-evidence-r1.tar.gz','graph-evidence-r1.tar.gz');(A/'pack.py').write_text(s)
