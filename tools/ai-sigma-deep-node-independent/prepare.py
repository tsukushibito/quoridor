import pathlib,json,hashlib,tarfile,subprocess,datetime,os
R=pathlib.Path(__file__).resolve().parents[2];T=R/'tools/ai-sigma-deep-node-independent';O=R/'.artifacts/ai-sigma/resume-20261002/DEEP-NODE-INDEPENDENT';D=R/'research-data/ai-sigma/132-deep-node-comparison';sha=lambda b:hashlib.sha256(b).hexdigest()
(O/'runs').mkdir(exist_ok=True)
checks={}
expected={'handoff-summary.json':'058a08cdfa7e7f47f7202bc45e730f50eb6da930a67e4dfcf52fa6c9401b3319','runtime-source-stopped-before-report.json':'e6bf3699666645cb4f66c4d0bf234b2e8dd4a2ecc300c333cdefde49d204d9e8','fixed-inputs.json':'fffc171a2b2fc5f36cab950299e651912fa95287ee0e6121bebb35d18bf56b01','all-attempts.tar.gz':'cd30c90ac72d14d75cb0cb30de8d723891c5f4fd223907b7cbc6d5e421fa7d43'}
for n,h in expected.items():assert sha((D/n).read_bytes())==h;checks[str(D/n)]=h
with tarfile.open(D/'all-attempts.tar.gz') as a:
 for n in ['runs/deep132-measure-r1/browser-result.json','build/trace.wasm','build/baseline.wasm']:
  b=a.extractfile(n).read();(O/pathlib.Path(n).name).write_bytes(b);checks[n]={'sha256':sha(b),'bytes':len(b)}
assert checks['build/trace.wasm']['sha256']=='6f050a754c512b0a160f519ac8924f0c9d887d9860121386536a076d44fa0b3d'
assert checks['build/baseline.wasm']['sha256']=='1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'
stop=json.loads((D/'runtime-source-stopped-before-report.json').read_text());live=[]
for x in stop['identities']:
 p=x.get('pid');tick=x.get('start_ticks',x.get('starttick'))
 try:
  s=pathlib.Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()
  if int(s[19])==tick:live.append(x)
 except FileNotFoundError:pass
assert not live
source=[]
for n in ['adapters.cjs','browser.cjs','deep-main.js','deep-input.js','deep-worker.js']:
 p=R/'tools/ai-sigma-deep-node-comparison'/n;h=sha(p.read_bytes());g=subprocess.check_output(['git','show','edbf29ac:'+str(p.relative_to(R))],cwd=R);assert sha(g)==h;source.append({'path':str(p.relative_to(R)),'sha256':h})
model=R/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';assert sha(model.read_bytes())=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'
runner=(R/'tools/ai-sigma-completed-fpu-independent/runner.py').read_text().replace('COMPLETED-FPU-INDEPENDENT','DEEP-NODE-INDEPENDENT').replace('125-completed-fpu-independent','133-deep-node-independent').replace('quoridor-4lc.125','quoridor-4lc.133').replace("CONFIG['frame']==8","CONFIG['frame']==9").replace('p125-','p133-').replace('else 120','else 180').replace('else 240','else 300');(T/'runner.py').write_text(runner)
browser=(R/'tools/ai-sigma-deep-node-comparison/browser.cjs').read_text().replace("require('./adapters.cjs')","require('../ai-sigma-deep-node-comparison/adapters.cjs')").replace("__dirname+'/deep-input.js'","ROOT+'/tools/ai-sigma-deep-node-comparison/deep-input.js'").replace("ROOT+'/.artifacts/ai-sigma/resume-20261002/DEEP-NODE-COMPARISON/build/trace.wasm'","ROOT+'/.artifacts/ai-sigma/resume-20261002/DEEP-NODE-INDEPENDENT/trace.wasm'").replace("ROOT+'/.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm'","ROOT+'/.artifacts/ai-sigma/resume-20261002/DEEP-NODE-INDEPENDENT/baseline.wasm'");(T/'browser.cjs').write_text(browser)
config={'issue':'quoridor-4lc.133','frame':9,'kind':'count','run_id':'p133-count-r1','processing_deadline':'2026-10-02T17:15:32Z','newjob_deadline':'2026-10-02T17:10:32Z','seed':1979,'count_timeout_ms':30000,'searches':[{'fixture_id':'diverse-prefix-mid-pair2-color2-new8','engine':'candidate','K':32},{'fixture_id':'diverse-prefix-mid-pair2-color2-new8','engine':'reference','K':32},{'fixture_id':'diverse-prefix-mid-pair2-color2-new16','engine':'reference','K':32},{'fixture_id':'diverse-prefix-mid-pair2-color2-new16','engine':'candidate','K':32}],'startup_separate':6,'tracecap':8,'new_games':0,'selection_result_before':True}
(O/'config.json').write_text(json.dumps(config,indent=2)+'\n');(O/'input-before.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'source':source,'owner132_identity_count':len(stop['identities']),'owner132_current_same_identity':live,'currentabsence_not_natural_allperiod':True,'model_SHA':sha(model.read_bytes())},indent=2)+'\n')
print(json.dumps({'hashes_matched':len(checks),'source_matched':len(source),'current0':len(stop['identities']),'saved_raw_bytes':(O/'browser-result.json').stat().st_size}))
