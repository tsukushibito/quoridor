import asyncio,importlib.util,json,subprocess,sys,datetime,os
from pathlib import Path
MAIN=Path('/workspaces/quoridor');OUT=Path(__file__).parent
sp=importlib.util.spec_from_file_location('team',MAIN/'scripts/dev/research-team.py');team=importlib.util.module_from_spec(sp);sp.loader.exec_module(team)
async def main():
 for issue in ('quoridor-4lc','quoridor-4lc.92'):team.require_issue(issue,MAIN)
 registry=team.load_registry(MAIN/'.artifacts/research-team/registry.json',MAIN);sender=team.role_entry(registry,'steward');assert os.getenv('CODEX_THREAD_ID')==sender['thread_id'],'Unexpected reporting thread'
 host=json.loads(subprocess.check_output(['codex','app-server','daemon','version'],timeout=5,text=True))
 async with team.AppServer(host,timeout=6) as server:
  with team.dispatch_lock(MAIN):
   for issue in ('quoridor-4lc','quoridor-4lc.92'):team.require_issue(issue,MAIN)
   target=team.role_entry(registry,'coordinator')['thread_id']
   result={'delivered':True,'receipt':await server.deliver(target,Path(sys.argv[1]).read_text())}
   result['at']=datetime.datetime.now(datetime.timezone.utc).isoformat();print(json.dumps(result,ensure_ascii=False))
asyncio.run(main())
