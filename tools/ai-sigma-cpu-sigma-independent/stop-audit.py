from pathlib import Path
import json,hashlib,tarfile,datetime,subprocess
R=Path.cwd();O=R/'.artifacts/ai-sigma/resume-20261002/CPU-SIGMA-INDEPENDENT';D=R/'research-data/ai-sigma/117-cpu-sigma-comparison';checks={};evidence=[]
def h(b):return hashlib.sha256(b).hexdigest()
for i in range(1,7):
 name=f'cpu117-pair{i}-r1';m=json.loads((D/(name+'.manifest.json')).read_text());by={x['path']:x['SHA256'] for x in m['members']}
 with tarfile.open(D/(name+'.tar.gz')) as tf:
  selected={}
  for n in ['config','finally-model-drop','main-timers-stop','outer-controlled-stop','pause-monitor-stop','source-bindings','summary']:
   path=f'runs/{name}/{n}.json';b=tf.extractfile(path).read();assert h(b)==by[path];checks[name+':'+path]=h(b);selected[n]=json.loads(b)
  processpath=f'runs/{name}.process.json';b=tf.extractfile(processpath).read();assert h(b)==by[processpath];p=json.loads(b);checks[name+':'+processpath]=h(b)
  e={'run':name,'runtime_Git':selected['summary'].get('Git'),'config_Git':selected['config'].get('Git'),'primary':selected['summary']['primary'],'secondary':selected['summary']['secondary'],'Modeldrop':selected['finally-model-drop'],'main_stop':selected['main-timers-stop'],'controlledstop':selected['outer-controlled-stop'],'monitor':selected['pause-monitor-stop'],'source_bindings':selected['source-bindings'],'outer':{k:p[k] for k in ['exit','stop_reason','remaining','unknown_adopted','kernel_identity_count','kernel_adoptions']}};evidence.append(e)
  assert e['primary'] is None and not e['secondary']
# Verify input scripts used by browser against saved per-run bindings.
current=json.loads((O/'runs/p118-saved-r2/source-bindings.json').read_text());assert all(x['source_bindings']==current for x in evidence)
stop=json.loads((D/'runtime-source-stopped-before-report.json').read_text());after={p:h((R/p).read_bytes()) for p in stop['source_after']};assert after==stop['source_after']
proof=[]
for git in ['9eb3510b01e47d5e49e6f0412937c80223b71fb0','db3bdc029a049e7feed1c5da9624786ba9419e9e']:
 for p in ['tools/ai-sigma-cpu-sigma-frame8/adapters.cjs','tools/ai-sigma-cpu-sigma-frame8/browser-glue.js']+[x['path'] for x in current.values()]:
  b=subprocess.check_output(['git','show',git+':'+p]);assert h(b)==h((R/p).read_bytes());proof.append({'Git':git,'path':p,'SHA':h(b)})
model='models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';wasm='.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm';assets={model:h((R/model).read_bytes()),wasm:h((R/wasm).read_bytes())};assert assets[model]=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d' and assets[wasm]=='1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01'
(O/'owner-stop-source-audit.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'necessary_member_checks':checks,'evidence':evidence,'runtime_source_Git_checks':proof,'source_after':after,'asset_refs':assets,'pair4_admission_not_retroactively_passed':True,'inner_controlled_outer_wait_currentabsence_distinct':True},indent=2)+'\n')
print(json.dumps({'checked_stop_source_members':len(checks),'source_Git_checks':len(proof),'pairprimary':0,'pairsecondary':0,'source_after':len(after)}))
