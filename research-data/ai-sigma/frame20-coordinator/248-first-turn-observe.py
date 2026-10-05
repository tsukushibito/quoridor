import asyncio,importlib.util,json,pathlib,datetime
P=pathlib.Path('research-data/ai-sigma/frame20-coordinator')
spec=importlib.util.spec_from_file_location('team','/workspaces/quoridor/scripts/dev/research-team.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
 host=m.command_json(['codex','app-server','daemon','version'])
 async with m.AppServer(host,timeout=20) as app:
  ts=await app.turns('01a0f31c-2e4b-7170-82c5-69e1428c2418',1)
  t=ts[0];out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_turn':'01a109a6-8d05-79f0-8b57-8b68cd91c29e','turn':{k:t.get(k) for k in ['id','status','error','startedAt','completedAt']},'item_types':[x.get('type') for x in t.get('items',[])]}
  (P/'248-first-turn-observe.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
asyncio.run(main())
