import json,pathlib,hashlib,subprocess,tarfile,datetime,os
R=pathlib.Path(__file__).resolve().parents[2];P=R/'research-data/ai-sigma/142-wallless-oracle';D=R/'research-data/ai-sigma/143-wallless-label-independent';O=R/'.artifacts/ai-sigma/resume-20261002/WALLLESS-LABEL-INDEPENDENT'
sha=lambda b:hashlib.sha256(b).hexdigest();refs=[]
def fixed(n,h=None):
 b=(P/n).read_bytes();assert b==subprocess.check_output(['git','show','63d46dd:'+str((P/n).relative_to(R))]);assert not h or sha(b)==h;refs.append({'path':str((P/n).relative_to(R)),'SHA256':sha(b),'Git':'63d46dd'});return json.loads(b)
handoff=fixed('handoff-summary.json','9b091fc47bfe95e93fd860ea44d6886f1a35d4cb60ababcee5950f7a9c34ede2');stop=fixed('runtime-source-stopped-before-report.json','3dc910cd05a94ca4fc07c81920bba246ccf0ee224e4bc5d08197730dc7a03a31');final=fixed('final-source-stop.json','071a90d7206ca4385aa708679e6c6e1344cf20a48f0a956673eda3745f160a70');reg=fixed('preregister.json');m=fixed('archive-manifest.json');arc=P/'runs.tar.gz';assert sha(arc.read_bytes())=='5aa75aeb9c640d0dceb91de026da08535face3086a23287adc8b182f8d570b60';mm={x['name']:x for x in m['members']};a=tarfile.open(arc)
def member(n):
 b=a.extractfile(n).read();x=mm[n];assert len(b)==x['bytes'] and sha(b)==x['sha256'];refs.append({'member':n,'bytes':len(b),'SHA256':sha(b)});return json.loads(b)
samples=[]
for i in range(2):
 g=member('p142-oracle-r2/generation-'+str(i)+'.json');label=member('p142-oracle-r2/label-'+str(i)+'.json');assert len(g['attempts'])==1 and g['adopted']['attempt']==0 and g['attempts'][0]['error'] is None;samples.append({'generation':g,'label':label})
receipts={n:member('p142-oracle-r2/'+n+'.json') for n in ['browser-status','controlled-stop','pause-monitor-stop','actual-served-source']}
receipts['outer']=member('p142-oracle-r2.owned-ack.json')
input={'reg':reg,'samples':samples};(O/'input.json').write_text(json.dumps(input)+'\n')
current=0;detail=[];seen=set()
for parent in [R/'.artifacts/ai-sigma/continuation-20261001',R/'.artifacts/ai-sigma/resume-20261002']:
 for folder in parent.iterdir():
  if not folder.is_dir() or not any(k in folder.name for k in ['CRITIC','INDEPENDENT','EVALUATION-PLAN']):continue
  size=0
  for p in folder.rglob('*'):
   if not p.is_file():continue
   s=p.stat();key=(s.st_dev,s.st_ino)
   if key not in seen:seen.add(key);size+=s.st_blocks*512
  current+=size;detail.append({'path':str(folder.relative_to(R)),'allocated':size})
assert current+8*1024**2<112*1024**2
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'refs':refs,'proof_input_bytes':(O/'input.json').stat().st_size,'upstream_stop':stop,'upstream_final_source':final,'raw_receipts':receipts,'critic_artifact_current_allocated':current,'forecast_new':8*1024**2,'combined_guard':112*1024**2,'reservation_new':0,'old_unknown_not_decreased':True,'storage_details':detail,'input_SHA256':sha((O/'input.json').read_bytes()),'source_hash_before':{str(p.relative_to(R)):sha(p.read_bytes()) for folder in [pathlib.Path(__file__).parent,R/'tools/ai-sigma-actual-boundary-repair'] for p in folder.iterdir() if p.is_file() and (folder==pathlib.Path(__file__).parent or p.name in ['game.js','context.js','cleanup.cjs','pause-check.cjs','kernel_boundary.py','owned_ledger.py'])}}
(D/'input-and-binding.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['critic_artifact_current_allocated','forecast_new','proof_input_bytes','input_SHA256']}))
