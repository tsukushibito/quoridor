import pathlib,json,subprocess,hashlib,collections,datetime
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/frame10-gap-design'
g='9bafd9ef12298d2b587599f12ea02b4ba5f21123';refs=[]
for p in ['docs/design/ai-sigma-frame10-gap-preregister-supplement.md','research-data/ai-sigma/frame10-coordinator-start/adopted-seeds.json']:
 b=(R/p).read_bytes();assert b==subprocess.check_output(['git','show',g+':'+p]);h=hashlib.sha256(b).hexdigest();refs.append(dict(path=p,Git=g,SHA256=h,bytes=len(b)))
 if p.endswith('.json'):
  assert h=='a82f2d01875180aa6a4a53be6e62d1ae11b9ab01ef2b3d37e5a1b40a7ede5c04';seeds=json.loads(b)
s=seeds['slots'];assert len(s)==32 and [x['slot'] for x in s]==list(range(1,33))
assert collections.Counter(x['layer_ply'] for x in s)=={4:8,5:8,12:8,13:8}
for block in range(1,9):
 rows=[x for x in s if x['block']==block];assert len(rows)==4 and set(x['layer_ply'] for x in rows)=={4,5,12,13}
 assert all(x['candidate_color_order']==([1,2] if block%2 else [2,1]) for x in rows)
assert all(x['search_seed_both']==1979 and len(x['attempt_seeds'])==8 and all(0<k<2**32 for k in x['attempt_seeds']) for x in s)
result=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),issue='quoridor-4lc.147',refs=refs,slots=32,game_slots=64,attempt_seed_count=256,seed_collision_count=256-len(set(k for x in s for k in x['attempt_seeds'])),layer_and_color_order_check=True,
 adopted=['strata4/5/12/13 each8','master61041/hash-mixed seeded table','all64 slots denominator/missing intervals','round-robin strata and color alternating','samewall primary/quantity separate/conditional exploratory Hoeffding','old119 all8 signatures excluded independently of WDL','maximum8attempt not proposed100','new-set history/state duplicates retained'],
 not_adopted=['samecompleted automatic games','C145 policy selection','new balance/prior filter'],
 dissent='No major objection preventing this finite diagnostic; exclusion makes target conditional on being unlike all8 old signatures and max8first-nonterminal attempts. Random legal, hash-mixed seeds, class variation and color swap do not certify representative states or independent game runtime; root-prior-only saturation remains possible.',
 primary_operation_fault_quality_asymmetry='candidate fault operational loss kept separately; reference fault is unknown, so pure terminal quality must also mark candidate faults unknown and label operational vs pure-quality intervals distinctly.',
 execution_gate_added=False,NN_Chrome_game=0)
(D/'adoption.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['slots','game_slots','attempt_seed_count','seed_collision_count','layer_and_color_order_check']}))
