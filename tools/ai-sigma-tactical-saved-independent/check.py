import pathlib,json,hashlib,tarfile,subprocess,datetime
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/TACTICAL-SAVED-INDEPENDENT';D=R/'research-data/ai-sigma/131-tactical-saved-independent';B=R/'research-data/ai-sigma/129-tactical-evaluation';h=lambda b:hashlib.sha256(b).hexdigest();checks={}
expected={'handoff-summary.json':'fa9d8b0eedfa7e1c2f085c9654f5819dd61a8f7387ead9f112e6d29d2c264516','runtime-source-stopped-before-report.json':'343f6ce4e3c05d319222edb78a32eb9b7edf63aebbe5480f662be2964a8f21ad','runs-all-attempts.tar.gz':'fc0b8cb2a85221bc61e5b4b30fd258d772cd88327dfff57337084c3a00be0a45'}
for n,e in expected.items():b=(B/n).read_bytes();assert h(b)==e;checks[str((B/n).relative_to(R))]=h(b)
lp=R/'research-data/ai-sigma/127-tactical-oracle/labels-and-inputs.json';lb=lp.read_bytes();assert h(lb)=='0c63b9eb1450d824c45786c3c73aec62f0908f87d4d14f14eacaefed7b8adc26';assert subprocess.check_output(['git','show','3061661:'+str(lp.relative_to(R))],cwd=R)==lb;checks[str(lp.relative_to(R))]=h(lb)
manifest=json.loads((B/'archive-manifest.json').read_text());items=manifest['members'];print('member schema',str(items[0])[:180])
ledger={};raw=None;small={}
with tarfile.open(B/'runs-all-attempts.tar.gz') as a:
 for m in a.getmembers():
  if m.name.endswith(('browser-result.json','source-bindings.json','finally-model-drop.json','main-timers-stop.json','pause-monitor-stop.json','outer-controlled-stop.json','.process.json','startup.json','summary.json')):
   b=a.extractfile(m).read();ledger[m.name]=h(b)
   if m.name.endswith('browser-result.json'):raw=json.loads(b)
   else:small[m.name]=json.loads(b)
# hashes are independently calculated before parsing; owner manifest is checked as evidence, not substituted for own arithmetic.
for n,digest in ledger.items():
 entry=next(x for x in items if x.get('member',x.get('path',x.get('name')))==n);assert entry.get('SHA256',entry.get('sha256'))==digest,(n,entry)
checks.update(ledger)
stop=json.loads((B/'runtime-source-stopped-before-report.json').read_text());ids=set()
def walk(x):
 if isinstance(x,dict):
  p=x.get('pid',x.get('runner_pid'));t=x.get('start_ticks',x.get('starttick',x.get('runner_starttick')))
  if isinstance(p,int) and isinstance(t,int):ids.add((p,t))
  for y in x.values():walk(y)
 elif isinstance(x,list):
  for y in x:walk(y)
walk(stop);walk(small);live=[]
for p,t in ids:
 try:
  s=pathlib.Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()
  if int(s[19])==t:live.append({'pid':p,'starttick':t,'state':s[0]})
 except (FileNotFoundError,ProcessLookupError):pass
assert not live
before={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'original_identity_denominator':len(ids),'same_identity_current':live,'archive_total_members':len(items),'necessary_members':len(ledger),'whole_archive_SHA_checked':True,'critic_preexisting_conservative_bytes':85*1024*1024,'new_forecast_bytes':2*1024*1024,'combined_guard':112*1024*1024,'reservation_add':0};(O/'input-before.json').write_text(json.dumps(before,indent=2)+'\n');(D/'input-before.json').write_text(json.dumps(before,indent=2)+'\n');(D/'original-necessary-stop.json').write_text(json.dumps(small,indent=2)+'\n')
cp=subprocess.run(['node','--max-old-space-size=192','--max-semi-space-size=4','--no-node-snapshot',str(R/'tools/ai-sigma-tactical-saved-independent/check.cjs'),str(D/'independent-results.json')],input=json.dumps({'raw':raw,'labels':json.loads(lb)}),text=True,cwd=R);assert cp.returncode==0
# Actual served body binding is checked without executing producer/Worker/NN.
code="const fs=require('fs'),c=require('crypto'),a=require('./tools/ai-sigma-tactical-evaluation/adapters.cjs');console.log(JSON.stringify(Object.fromEntries(['main','worker','producer','checkpoint','cache'].map(n=>[n,c.createHash('sha256').update(a.script(n)).digest('hex')]))));"
served=json.loads(subprocess.check_output(['node','--max-old-space-size=192','-e',code],cwd=R,text=True));bindings=small['runs/tactical129-measure-r1/source-bindings.json'];assert all(bindings[n]['adapted_SHA256']==v for n,v in served.items())
source=[]
paths=['tools/ai-sigma-tactical-evaluation/adapters.cjs','tools/ai-sigma-tactical-evaluation/tactical-main.js','tools/ai-sigma-player-workers/player-main.js','tools/ai-sigma-player-workers/player-worker.js','tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js','tools/ai-sigma-cp-frame/shared-best-action.cjs']
for p in paths:
 b=(R/p).read_bytes();g=subprocess.check_output(['git','show','766605299347c46869a2154afe27412162917d2f:'+p],cwd=R);assert b==g;source.append({'path':p,'SHA256':h(b),'measured_Git_equal':True});checks[p]=h(b)
(D/'served-source-and-Git.json').write_text(json.dumps({'served_SHA256':served,'saved_bindings_match':True,'source':source,'new_Worker_executed':False},indent=2)+'\n')
after={p:h((R/p).read_bytes()) for p in checks if not p.startswith('runs/')};assert all(after[p]==checks[p] for p in after);(D/'input-after.json').write_text(json.dumps({'checks':after,'all_equal':True,'raw_from_same_frozen_archive':True},indent=2)+'\n');print(json.dumps({'success':True,'saved_publics':len(raw['rows']),'original_current0':len(ids),'newNN':0}))
