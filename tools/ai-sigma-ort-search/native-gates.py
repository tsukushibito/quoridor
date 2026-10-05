import pathlib,json,subprocess
ROOT=pathlib.Path.cwd();RUN=ROOT/'../../.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH';OLD=ROOT/'../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE';CACHE=pathlib.Path('/home/vscode/.cache/inference/research/ai-sigma/ort-search/target/release')
subprocess.run([str(CACHE/'numeric')],check=True)
rows=[]
for case in ['initial','opening','walled-midgame','p2','jump-p2','many-walls']:
 raw=subprocess.check_output([str(CACHE/'b0-control'),case,'off','1']);(RUN/f'b0-{case}.jsonl').write_bytes(raw);got=[json.loads(l) for l in raw.splitlines()];expected=[json.loads(l) for l in (OLD/f'compare-{case}-0-original.jsonl').read_bytes().splitlines()]
 assert got[0]==expected[0],case+' rules';a,b=got[1],expected[1]
 for key in ['action','stats','root_edges_bits']:assert a[key]==b[key],(case,key)
 rows.append({'case':case,'rules_exact':True,'action_stats_visits_prior_value_bits_exact':True})
(RUN/'b0-gate.json').write_text(json.dumps({'rows':rows,'failures':0,'limits':{'sims':192,'nodes':512,'depth':24,'seed':1979,'step':4},'features':'research diagnostics compiled; standard b0 constructor context=None; profiling off'},indent=2));print('native28 and B0 six exact')
