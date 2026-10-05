import asyncio,datetime,importlib.util,json,pathlib
P=pathlib.Path('research-data/ai-sigma/frame20-coordinator')
spec=importlib.util.spec_from_file_location('team','/workspaces/quoridor/scripts/dev/research-team.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
 host=m.command_json(['codex','app-server','daemon','version'])
 async with m.AppServer(host,timeout=20) as app:
  tid='01a0f2e9-357d-7ef3-a2fe-b16f80accda5';thread=await app.read_thread(tid)
  out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':thread['status']['type'],'RPC':False,'body':'root-initial-handoff.md'}
  if out['status']=='active':
   turns=await app.turns(tid,1);turn=turns[0]
   with m.dispatch_lock(pathlib.Path('/workspaces/quoridor')):
    out['result']=await app.request('turn/steer',{'threadId':tid,'expectedTurnId':turn['id'],'input':[{'type':'text','text':(P/'root-initial-handoff.md').read_text(),'text_elements':[]}]});out['RPC']=True;out['turn_id']=turn['id']
  else: out['reason']='ROOT_IDLE_NO_ACK_START'
  (P/'root-handoff-delivery.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
asyncio.run(main())
