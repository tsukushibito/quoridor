import asyncio,datetime,hashlib,importlib.util,json,pathlib,sys
ROOT=pathlib.Path('/workspaces/quoridor'); CWD=ROOT/'.worktree/ai-sigma'; OUT=CWD/'.artifacts/ai-sigma/resume-20261002'
spec=importlib.util.spec_from_file_location('team',ROOT/'scripts/dev/research-team.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
async def main():
 role,issue,filename=sys.argv[1:]; prefix=pathlib.Path(filename).stem
 with m.dispatch_lock(ROOT):
  m.require_issue('quoridor-4lc',ROOT);m.require_issue(issue,ROOT)
  registry=m.load_registry(ROOT/'.artifacts/research-team/registry.json',ROOT);host=m.command_json(['codex','app-server','daemon','version'])
  async with m.AppServer(host,timeout=20) as s:
   # Session count is not an admission condition. Inspect only the recipient;
   # deliver() selects its current exact turn for steer, or starts an idle role.
   target_id=('01a0f2e9-357d-7ef3-a2fe-b16f80accda5' if role=='root'
              else m.role_entry(registry,role)['thread_id'])
   target=await s.read_thread(target_id);states={role:target['status']['type']}
   if filename=='root-review96-ack.md' and states[role]!='active':
    (OUT/(prefix+'-deferred.json')).write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'states':states,'RPC':False,'reason':'ACK_STEER_ONLY_NO_ROOT_RESTART'},indent=2)+'\n');print('DEFERRED_ROOT_IDLE');return
   body=(OUT/filename).read_text();intent=OUT/(prefix+'-intent.json');receipt=OUT/(prefix+'-delivery.json')
   if receipt.exists():raise RuntimeError('existing receipt: inspect before resending')
   intent.write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':target_id,'states':states,'body_sha256':hashlib.sha256(body.encode()).hexdigest()},indent=2)+'\n')
   r=await s.deliver(target_id,body,None if role=='root' else str(CWD));r.update(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),states_before=states);receipt.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__ == '__main__':
 asyncio.run(main())
