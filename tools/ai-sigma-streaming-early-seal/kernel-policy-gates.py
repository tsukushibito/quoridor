import os,json
from pathlib import Path
from kernel_boundary import Boundary
from owned_ledger import Ledger
base=Path(__file__).resolve().parents[2]/'.artifacts/ai-sigma/continuation-20261001/SIGMA-KERNEL-OWNERSHIP';events=[];ev=lambda kind,**v:events.append({'kind':kind,**v});launcher={'pid':40000,'start_ticks':100,'ppid':0};root={'pid':40001,'start_ticks':101,'ppid':40000};b=Boundary(launcher,'unitboot',ev);b.reserve_root();b.audit('subprocess.Popen',());b.bind_root(root)
t={40000:launcher,40001:root,40002:{'pid':40002,'start_ticks':102,'ppid':40000,'state':'Z','pgid':50000}};ids=b.observe(t);assert (40002,102) in ids and b.may_wait(t[40002])
assert not b.may_wait({'pid':40002,'start_ticks':103,'ppid':40000})
try:b.audit('subprocess.Popen',())
except RuntimeError:pass
else:raise AssertionError('second spawn accepted')
assert not b.valid
# Fake registration of a live non-descendant must fail before any signal/wait.
p=base/'fake-policy-ledger.jsonl';ack=base/'fake-policy-ack.json';ledger=Ledger(p,ack,root,'unitboot',ev);fake={'boot_id':'unitboot','root':{'pid':40001,'starttick':101},'identity':{'pid':40003,'starttick':104,'ppid':40001},'parent':{'pid':40001,'starttick':101},'UTC':'unit'};p.write_text(json.dumps(fake)+'\n');ledger.read({40003:{'pid':40003,'start_ticks':104,'ppid':77777}},(),{},b);assert ledger.rejected['40003:104']=='PARENT_EDGE_NOT_PROVED'
(base/'kernel-policy-summary.json').write_text(json.dumps({'tests':['sole root bootstrap','direct kernel adoption without polled ancestor','same PID wrong starttick no wait','second spawn invalidates/fresh forbidden','fake external parent edge refused'],'events':events,'signal_calls':0,'reap_calls':0,'NN':0},indent=2)+'\n');print('kernel policy passed')
