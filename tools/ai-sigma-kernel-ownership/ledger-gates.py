import tempfile,json,os
from pathlib import Path
from owned_ledger import Ledger
base=Path(__file__).resolve().parents[2]/'.artifacts/ai-sigma/continuation-20261001/SIGMA-DETACHED-OWNERSHIP';events=[];root={'pid':40000,'start_ticks':111};path=base/'unit-ledger.jsonl';ack=base/'unit-ack.json';boot='fixed-test-boot';ledger=Ledger(path,ack,root,boot,lambda kind,**v:events.append({'kind':kind,**v}))
def row(pid,tick,parentpid=40000,parenttick=111):return {'boot_id':boot,'root':{'pid':40000,'starttick':111},'identity':{'pid':pid,'starttick':tick,'ppid':parentpid,'pgid':pid,'state':'Z'},'parent':{'pid':parentpid,'starttick':parenttick},'UTC':'fixed'}
rows=[row(40001,112),row(40002,113,40001,112),row(40003,114,99999,0),row(40004,115),row(os.getpid(),777)];path.write_text(''.join(json.dumps(x)+'\n' for x in rows));t={40002:{'pid':40002,'start_ticks':113,'ppid':os.getpid(),'state':'Z'},40004:{'pid':40004,'start_ticks':999,'ppid':os.getpid(),'state':'S'}};ledger.read(t)
assert '40002:113' in ledger.accepted and '40003:114' in ledger.rejected and ledger.rejected['40004:115']=='PID_REUSED' and f'{os.getpid()}:777' in ledger.rejected
assert len(ledger.live(t))==1 and ledger.live(t)[0]['pid']==40002
(base/'ledger-unit-summary.json').write_text(json.dumps({'events':events,'tests':['group_empty_owned_Z_live','unknown_parent_refused','PID_reuse_refused','monitor_self_refused','transitive_known_parent_after_detach','boot_bound'],'signal_calls':0,'NN':0},indent=2))
print('ledger gates passed')
