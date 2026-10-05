import pathlib,json,statistics,math,hashlib,os,datetime
ROOT=pathlib.Path('../..').resolve();RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH';CACHE=pathlib.Path('/home/vscode/.cache/inference/research/ai-sigma/ort-search');v=json.loads((RUN/'browser-latency-registered.json').read_text());pre=json.loads((RUN/'latency-preregister.json').read_text());assert len(v['rows'])==78
for row,entry in zip(v['rows'],pre['schedule']):assert all(row[k]==entry[k] for k in ['id','backend','sample','warmup'])
mut=[rel for rel,h in pre['source_hashes'].items() if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=h];assert not mut
assert hashlib.sha256((CACHE/'target/wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm').read_bytes()).hexdigest()==pre['B_wasm_sha256']
def metrics(a):
 if not a:return None
 a=sorted(a);return {'n':len(a),'p50':statistics.median(a),'p95_nearest_rank':a[math.ceil(.95*len(a))-1],'max':max(a),'min':min(a)}
results=[]
for fid in ['initial-p1','asym-hv-p2','straight-jump-p2']:
 group={}
 for backend in ['A','B']:
  rows=[r for r in v['rows'] if r['id']==fid and r['backend']==backend and not r['warmup']];assert len(rows)==10
  nn=[]
  for r in rows:
   if backend=='A' and r['cp']:nn += [s['nn_end_ms']-s['feature_end_ms'] for s in r['cp'].get('spans',[])]
   if backend=='B':nn += [s['nn_ms'] for s in r['spans'] if s['kind']=='NN']
  group[backend]={'elapsed_ms':metrics([r['elapsed_ms'] for r in rows]),'simulations_success_only':metrics([r['cp']['simulations'] for r in rows if r['valid']]),'simulations':metrics([r['cp']['simulations'] if r['valid'] else 0 for r in rows]),'completed_internal_trace':metrics([max([s.get('sims',0) for s in r['spans'] if s['kind']=='step']+[0]) for r in rows]),'NN_attempts':metrics([r['calls'] for r in rows]),'NN_ms_per_call':metrics(nn),'invalid':sum(not r['valid'] for r in rows),'errors':[r['error'] for r in rows if r['error']],'overshoot_ms':metrics([r['overshoot_ms'] for r in rows]),'arena_bytes_max':max([r['cp']['arena_bytes'] for r in rows if r['cp']]+[0]),'linear_bytes_max':max([r.get('memory',0) for r in rows]),'cap_flags':sum(bool(r['cp'] and r['cp']['cap']) for r in rows),'fallbacks':sum(r['fallback'] for r in rows),'actions':[r['accepted_action'] for r in rows],'serialization_ms':metrics([r['serialization_ms'] for r in rows]),'transport_ms':metrics([r['delivered']-(r['worker_delivery_send_ms']-v['clock']['offset_ms']) for r in rows])}
 results.append({'id':fid,'variants':group,'median_sim_B_over_A':group['B']['simulations']['p50']/group['A']['simulations']['p50'] if group['A']['simulations'] and group['B']['simulations'] else None})
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results,'planned':60,'measured':sum(not r['warmup'] for r in v['rows']),'warmup':sum(r['warmup'] for r in v['rows']),'invalid_rows':[{k:r.get(k) for k in ['id','backend','sample','warmup','error','elapsed_ms','calls','accepted_action']} for r in v['rows'] if not r['valid']],'invalid_total':sum(not r['valid'] for r in v['rows'] if not r['warmup']),'warmup_invalid':sum(not r['valid'] for r in v['rows'] if r['warmup']),'raw':str(RUN/'browser-latency-registered.json'),'clock':v['clock'],'source_mutations':mut,'zero_accepted_sim_means_known_no_valid_checkpoint_not_missing_NN_imputation':True,'ORT_memory_not_in_Rust_linear':True,'RSS_both_resident_models_not_variant_attributable':True,'classification':'fixed-T exploratory useful search quantity; not strength/quality; fixed-work speed no dedicated replication; p95 n10 equals max','competing':['A tract common Rust','B separated ORT pending/resume','C B0','H1backend','H2rules/select/finish/FPU','H3 NN/IPC/checkpoint/terminal denominators','H4small sample']}
(RUN/'latency-analysis-final.json').write_text(json.dumps(result,indent=2));print(json.dumps({'results':results,'invalid_total':result['invalid_total'],'warmup_invalid':result['warmup_invalid']},ensure_ascii=False))
