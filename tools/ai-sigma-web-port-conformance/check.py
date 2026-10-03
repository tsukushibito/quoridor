"""NN0 static source binding and independently derived fixture expectations."""
import collections,datetime,hashlib,json,math,pathlib,subprocess,struct
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/150-sigma-web-port-conformance';refs=[]
def read(p,git=True):
 b=(R/p).read_bytes();g=None
 if git:
  g=subprocess.check_output(['git','log','-1','--format=%H','--',p],text=True).strip()
  assert g and b==subprocess.check_output(['git','show',g+':'+p]),p
 refs.append(dict(path=p,Git=g,SHA256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
 return b.decode()
binding=json.loads(read('research-data/ai-sigma/130-deep-discrimination/source-binding.json'))
original=read('.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/mcts_worker.original.js',False)
assert hashlib.sha256(original.encode()).hexdigest()==binding['upstream_snapshot_SHA']
core=read('tools/ai-sigma-actual-boundary-repair/reference-core.js');control=read('tools/ai-sigma-actual-boundary-repair/reference-control-run.js');game=read('tools/ai-sigma-actual-boundary-repair/game.js');context=read('tools/ai-sigma-actual-boundary-repair/context.js');worker=read('tools/ai-sigma-actual-boundary-repair/early-worker.js')
def block(source,marker):
 start=source.index(marker);pos=source.index('{',start);depth=1;i=pos+1
 while depth:
  if source[i]=='{':depth+=1
  if source[i]=='}':depth-=1
  i+=1
 return source[start:i]
equal={}
for marker in ['class MCTSNode','function backup','function selectLeaf','function pickFromVisits']:
 a=block(original,marker);b=block(core,marker);assert a==b,marker;equal[marker]=dict(bytes_equal=True,SHA256=hashlib.sha256(a.encode()).hexdigest())
assert 'Math.sqrt(this.visitCount)' in core and 'score > bestScore' in core
assert 'if (c.visitCount > 0) visitedPriorSum += c.basePrior' in core
assert 'Math.exp(logits[i] - maxL)' in original and 'sumE += e' in original
assert 'value = leaf.state.winner() !== 0 ? -1 : 0' in original
assert 'const t=terminalResult(leaf.state)' in control and 'if(term){const root=new MCTSNode(state);completed(root);}' in worker
assert game.index('// ── H-wall ──')<game.index('// ── V-wall ──') and 'const key = `${p1k}|${p2k}|${nextParity}|${sortedH}|${sortedV}`' in game
read('docs/design/ai-sigma-contract-experiment-sigma-web-port.md')
deep=json.loads(read('research-data/ai-sigma/132-deep-node-comparison/final-results.json'));mean=json.loads(read('research-data/ai-sigma/140-candidate-true-mean-fpu/analysis.json'));dependency=json.loads(read('research-data/ai-sigma/140-candidate-true-mean-fpu/dependency-binding-final.json'))
assert deep['shared_roots']==4 and deep['shared_nonroot']==9 and deep['unshared_primary_nodes_per_engine']==19
assert sum(x['all_actual_select_prior_mean_ledger_checked'] for x in mean['actual_ledger_select_checks'])==280
f=json.loads(read('.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json',False))['fixtures'];g=json.loads(read('research-data/ai-sigma/frame10-baseline-gap/inputs.json'));read('research-data/ai-sigma/frame10-baseline-gap/preregister.json');read('research-data/ai-sigma/frame10-baseline-gap/user-direction-science-stop.json')
inputs=[next(x for x in f if x['id']==fid) for fid in ['initial-p1','asym-hv-p2','straight-jump-p2']]
for slot in [13,14]:
 p=next(x for x in g['prefixes'] if x['slot']==slot);assert p['accepted'] and p['attempt']==0;inputs.append(p['fixture'])
assert len(inputs)==5
features=[]
for x in inputs:
 if 'features_bits' in x:
  assert len(x['features_bits'])==648
  raw=struct.pack('<648I',*x['features_bits']);values=struct.unpack('<648f',raw)
 else:
  assert len(x['raw_features_float32'])==648
  values=x['raw_features_float32'];raw=struct.pack('<648f',*values)
 assert all(math.isfinite(v) for v in values)
 features.append(dict(id=x['id'],features648=True,features_bytes_SHA256=hashlib.sha256(raw).hexdigest()))
(D/'fixed-five-inputs.json').write_text(json.dumps({'kind':'saved exact5 machine diagnostics; legality declared upstream, new replay not executed','inputs':inputs},indent=2)+'\n')
# Independent arithmetic expectations for proposed artificial-oracle tests, not executing port/reference.
def first_max(a):return max(range(len(a)),key=lambda i:a[i])
assert first_max([0,0])==0 and first_max([1,1])==0 and first_max([0,2])==1
# Root model contributes once; leaf values are the current leaf player's perspective.
ledger=[.6,0,0];visits=[1,0,0]
for depth,value in [(1,-.4),(2,.8)]:
 for n in range(depth,-1,-1):ledger[n]+=value;visits[n]+=1;value=-value
assert all(abs(x-y)<1e-12 for x,y in zip(ledger,[1.8,-1.2,.8])) and visits==[3,2,1]
pq=ledger[0]/visits[0];fpu=pq-.2*math.sqrt(.25)
assert abs(pq-.6)<1e-12 and abs(fpu-.5)<1e-12
vp=[1,0,2,3,6,7,4,5]+[8+(7-y)*8+x for y in range(8) for x in range(8)]+[72+(7-y)*8+x for y in range(8) for x in range(8)]
assert len(vp)==136 and sorted(vp)==list(range(136)) and all(vp[vp[i]]==i for i in range(136))
wall_order=[(ori,x,y,8+(0 if ori=='h' else 64)+y*8+x,(81 if ori=='h' else 145)+y*8+x) for y in range(8) for x in range(8) for ori in ['h','v']]
assert [r[4] for r in wall_order[:4]]==[81,145,82,146]
result=dict(issue='quoridor-4lc.150',UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),refs=refs,four_functions_original_current_equal=equal,
 minimal_input_ids=[x['id'] for x in inputs],features=features,root_only_finish='all child visits0 -> original-order first, irrespective of max prior',sameK='rootN K/edgeK-1/loopK-1; terminal-noNN counted separately',
 arithmetic_expectations=dict(ledger=ledger,visits=visits,parentmean=pq,FPU_baseprior025=fpu,P2_permutation_involution=True,wall_first4_209=[r[4] for r in wall_order[:4]]),
 source_differences=['original root expands without terminal short circuit; research wrapper handles terminal root NN0','original stale cancel returnsnull; research adapter retains completed CP and discards stale return','research control yields/setTimeout and clocks/checkpoint versus upstream progress at~40 intervals','upstream NN error random rollout fallback; current fixed-model adapter strict faults','fullcanonical upstream based model-path; current fixed artifact explicitlyP2 canonical'],
 old_finite=dict(shared_roots=4,shared_nonroot=9,unshared_each19=True,actual_true_mean_select=280,fullDeep_proved=False),
 dependency_warning='140 necessary7library hashes/patch/currentmtime exist; Git-only binding insufficient; new private build must pin actual bytes, not claim old fullperiod dependency audit',
 scope=dict(NN=0,Chrome=0,build=0,game=0,port_executed=False,original_MCTS_executed=False,private151_source_edited=False),failures=[])
(D/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['four_functions_original_current_equal','minimal_input_ids','arithmetic_expectations','scope']}))
