import asyncio,datetime,json,pathlib,importlib.util
R=pathlib.Path('/workspaces/quoridor');C=R/'.worktree/ai-sigma';O=C/'.artifacts/ai-sigma/resume-20261002';D=C/'research-data/ai-sigma/frame16-coordinator'
spec=importlib.util.spec_from_file_location('team',R/'scripts/dev/research-team.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
 with m.dispatch_lock(R):
  m.require_issue('quoridor-4lc',R);m.require_issue('quoridor-4lc.92',R)
  host=m.command_json(['codex','app-server','daemon','version'])
  async with m.AppServer(host,timeout=20) as s:
   tid='01a0f6b5-b1bd-7752-b0bb-74a336e459a4';t=await s.read_thread(tid);status=t['status']['type'];now=datetime.datetime.now(datetime.timezone.utc).isoformat();p=D/'supervisor-architecture-active-only-delivery.json'
   if p.exists():print('receipt exists; no resend');return
   if status!='active':
    (D/'supervisor-architecture-deferred.json').write_text(json.dumps({'UTC':now,'status':status,'RPC':False,'reason':'natural-owned-active-only; no manual start'},indent=2)+'\n');print('idle deferred');return
   body=(O/'frame16-supervisor-architecture-mainplan-effect.md').read_text();r=await s.deliver(tid,body,str(C));r.update(UTC=now,status_before=status,manual_turn_started=False);p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
asyncio.run(main())
