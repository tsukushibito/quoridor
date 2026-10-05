import asyncio,importlib.util,json,pathlib,datetime
spec=importlib.util.spec_from_file_location('team','/workspaces/quoridor/scripts/dev/research-team.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
 host=m.command_json(['codex','app-server','daemon','version'])
 async with m.AppServer(host,timeout=20) as s:
  t=await s.read_thread('01a0f31c-2e4b-7170-82c5-69e1428c2418');print('hypothesis',t['status']['type'])
  if t['status']['type']=='active':
   with m.dispatch_lock(pathlib.Path('/workspaces/quoridor')):
    body='goal quoridor-4lc /227 finite acceptance。necessary11path303a9c327/e60d8e3b currentSHA/Gitbytes独立PASS・32syntheticNN0/sourceAPI停止/228owner APIcurrentSHA受領を支持。research-data/ai-sigma/frame18-coordinator/227-finite-adapter-acceptance.json。実学習未成立/旧180+180/4MiB/失敗保持。228は11:11:43実配分→本人claim/新静的開始、672max/量不足branch/同sample低LR/固定val-test sealへ採用済み。227見解→実adapter→主配分変更の有限成果。本人227close+backupをこの同実質turnで実施可、close専用turn不要。統括所有引継ぎCLIはholder保護拒否でforce/reclaim/代理actorなし、管理拒否は科学失敗ではない。新prep/新NN要求0。'
    a=await s.deliver(t['id'],body,str(pathlib.Path.cwd()));out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':a};print(json.dumps(out))
  else:out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'RPC':False,'deferred':'owner idle; no close-only newturn; acceptance saved'}
  pathlib.Path('research-data/ai-sigma/frame18-coordinator/227-acceptance-owner-delivery.json').write_text(json.dumps(out,indent=2)+'\n')
asyncio.run(main())
