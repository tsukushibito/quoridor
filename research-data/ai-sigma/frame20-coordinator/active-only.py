import asyncio,datetime,importlib.util,json,pathlib,sys
P=pathlib.Path('research-data/ai-sigma/frame20-coordinator')
spec=importlib.util.spec_from_file_location('team','/workspaces/quoridor/scripts/dev/research-team.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
 tid,name=sys.argv[1:]; receipt=P/(name+'-delivery.json');assert not receipt.exists(),'existing receipt: no blind retry'
 host=m.command_json(['codex','app-server','daemon','version'])
 async with m.AppServer(host,timeout=20) as app:
  thread=await app.read_thread(tid);out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':thread['status']['type'],'RPC':False,'body':name+'.md'}
  if out['status']=='active':
   turns=await app.turns(tid,1);turn=turns[0]
   with m.dispatch_lock(pathlib.Path('/workspaces/quoridor')):
    out['result']=await app.request('turn/steer',{'threadId':tid,'expectedTurnId':turn['id'],'input':[{'type':'text','text':(P/(name+'.md')).read_text(),'text_elements':[]}]});out['RPC']=True;out['turn_id']=turn['id']
  else:out['reason']='IDLE_NO_ACK_START'
  receipt.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
asyncio.run(main())
