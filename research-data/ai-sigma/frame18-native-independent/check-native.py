"""234: saved native receipt arithmetic only. Never imports or evaluates a model."""
import argparse,hashlib,json,math,struct,time,resource
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--task',required=True);ap.add_argument('--out',required=True);args=ap.parse_args();assert args.task=='native-234-saved-v1'
P=Path('research-data/ai-sigma/frame18-native-connection');t=time.monotonic();bound={}
def rd(p):
 p=Path(p);bound[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def near(x,y):assert math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-12),(x,y)
stop=rd(P/'science-stop.json');m=rd(P/'weight-manifest.json');par=rd(P/'parity-result.json');n=rd(P/'native-parity.json');s=rd(P/'search-result.json');fx=rd(P/'fixed-fixtures27.json');torch=rd(P/'torch-fixtures27.json')
b=Path(m['weights']).read_bytes();assert len(b)==m['weights_B']==48772 and hashlib.sha256(b).hexdigest()==m['weights_SHA'];v=struct.unpack('<12193f',b);assert all(math.isfinite(x)for x in v)
assert m['names']==['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias'] and m['shapes']==[[32,312],[32],[32,66],[32],[1,32],[1]]
sizes=[math.prod(x)for x in m['shapes']];assert sum(sizes)==12193 and m['little_endian_f32']==12193 and not m['h_export_recompensation']
scale=rd('research-data/ai-sigma/frame15-input-scale-control/scale.json');assert bound['research-data/ai-sigma/frame15-input-scale-control/scale.json']==m['scale_SHA'];assert scale['mu_f32']==m['mu_f32'] and scale['sigma_f32']==m['sigma_f32'] and all(x>0 for x in m['sigma_f32'])
assert len(fx)==27 and len({r['id']for r in fx})==27 and {r['id']for r in fx}=={r['id']for r in torch}
for r in fx:
 a,c=r['ids'];assert a==sorted(set(a)) and c==sorted(set(c)) and r['side']in[1,2]
 # Independent 180-degree/ownership relation between the two fixed-view feature lists.
 rot=[80-(a[1]-81),81+80-a[0]]
 rot += [162+63-(i-162) for i in a if 162<=i<226]
 rot += [226+63-(i-226) for i in a if 226<=i<290]
 rot += [290+(next(i for i in a if 301<=i<312)-301),301+(next(i for i in a if 290<=i<301)-290)]
 assert sorted(rot)==c
 assert len(r['distance'])==2 and all(math.isfinite(x)and 0<=x<=1 for x in r['distance'])
expect={r['id']:r['value']for r in torch};saved={r['id']:r['value']for r in n['roots']};saved.update({r['id']:r['native']for r in n['selected']});assert set(saved)==set(expect)
diff=[]
for k,x in saved.items():
 d=abs(x-expect[k]);assert d<=1e-5+1e-4*abs(expect[k]);diff.append(d)
near(max(diff),n['max_torch_abs']);near(n['max_torch_abs'],par['max_torch_abs']);assert n['tol']=={'abs':1e-5,'rtol':1e-4}
assert n['terminal_NN']==0 and n['parent_copy_buffer_key_history_unchanged'] and not n['mutable_undo_guarantee']
assert n['samples']==27+2*n['all_legal_children']==1057 and par['samples']==27+n['samples']==1084
summary=[];totalNN=0;walls=0;spans={};legal_counts=[]
for root in s['roots']:
 assert root['same_action']==(root['NNUE']['Action']==root['distance']['Action'])
 for model in ['NNUE','distance']:
  x=root[model];stats=x['stats'];assert stats['visited']==stats['processed']+stats['rejected_entry'];assert stats['processed']<=2048
  assert x['action_legal']and x['parent_copy_restored']and x['all_legal_actions_in_completed_root_depth']and x['last_completed_only']
  assert x['TT']==x['noise']==0 and not x['policy_exclusion'];completed=[d for d in x['depths']if 'completed_depth'in d];last=completed[-1]
  assert last['completed_depth']==x['completed_depth'] and last['Action']==x['Action'];near(last['value'],x['value'])
  assert sum(d['nodes_this_depth']for d in x['depths'])==stats['processed']
  if x['typed_stop']:
   assert x['typed_stop']=='NODE_CAP' and stats['processed']==2048 and stats['rejected_entry']==1
   assert x['depths'][-1]['status']=='INCOMPLETE'and not x['depths'][-1]['adopted'] and x['partial_depth_discarded']>x['completed_depth']
  else:assert stats['rejected_entry']==0 and x['completed_depth']==2
  if model=='NNUE':totalNN+=stats['NN'];legal_counts.append(completed[0]['root_all_actions'])
  else:assert stats['NN']==0
  walls+=x['wholewall_ms']
  for k,y in x['spans'].items():spans[k]=spans.get(k,0)+y
 summary.append({'id':root['id'],'NNUEdepth':root['NNUE']['completed_depth'],'Ddepth':root['distance']['completed_depth'],'NNUEAction':root['NNUE']['Action'],'DAction':root['distance']['Action'],'same_action':root['same_action'],'NNUEprocessed':root['NNUE']['stats']['processed'],'rejected_entry':root['NNUE']['stats']['rejected_entry']})
assert len(summary)==4 and sum(legal_counts)==515 and totalNN==s['samples']==4058
processes=[rd(P/'guardians'/name/'process.json')for name in ['parity-r1','search-r2']];assert sum(x['samples_actual']for x in processes)==stop['samples_actual']==5142
cost={'scientific_NN':5142,'Torch_parity':27,'native_parity':1057,'native_search':4058,'guardian_s':sum(x['wall_s']for x in processes),'root_wholewall_ms_sum':walls,'search_whole_ms':s['total_wholewall_ms'],'nonexclusive_spans_ms':spans,'terminal_span_largest':max(spans,key=spans.get)=='terminal_ms','initialization_recording_cleanup_not_rootspan':True}
near(cost['guardian_s'],stop['scientific_guardian_wall_s']);assert walls<=s['total_wholewall_ms']
failure=rd(P/'search-premodel-failure.json');cost['premodel_management_s']=failure['original_result']['wall_seconds'];cost['premodel_NN0_source_supplement']=failure['physicalNN'];cost['original_missing_counter_retained']=failure['original_counter_missing_preserved'];cost['background_wait_s_not_added']=stop['background_wait_s'];cost['total_team_management_UNKNOWN']=True
assert s['games4']['status']=='NOT_RUN'and len(stop['game_slots'])==4 and all(r['status']=='NOT_RUN'for r in stop['game_slots'])
for p,h in bound.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
out={'task':args.task,'schema':'native-independent-result-v1','PASS':True,'inputSHA':bound,'packing_sizes':sizes,'finite_f32_count':len(v),'fixture_P2_relation_checked':27,'saved_Torch_native_maxabs':max(diff),'full_delta_maxabs_receipt_only':n['max_full_delta_abs'],'all_children_receipt_bound':515,'root_diagnostics':summary,'cost':cost,'newNN':0,'limits':['No current forward, PT tensor-content reauthentication or full deep/minimax truth','SharedRuleA/P2/state fixture and full-delta receipt source dependency retained','Parent-copy restoration is not mutable undo certification','Rootmean is not exact leaf utility; history absent from model','Fixed order/warmcache and unequal completed depths prevent samewall strength claim','229 final curve/test/bootstrap remains NOT_RUN; not rerun here'],'next_max1':'Existing profiler points to terminal/legal-check cost: consider one reuse intervention with unchanged legality/history before wider policy or TT; no new job in234','calc_s':time.monotonic()-t,'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
Path(args.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['task','schema','PASS','saved_Torch_native_maxabs','root_diagnostics','cost','calc_s','peakRSS']}))
