import json
from admission import decide,base
cases=[]
for name,heavy,previous,error,zero in [('heavy',[{'pid':1}],[],False,True),('metadata',[],[],False,True),('readerror',[],[],True,True),('oldunknown',[],[{}],False,True),('dependency_unconfirmed',[],[],False,False)]:
 spawned=0
 try:
  decide(heavy,previous,error,zero);spawned+=1;ok=True
 except RuntimeError:ok=False
 assert ok==(name=='metadata') and spawned==(1 if name=='metadata' else 0)
 cases.append({'case':name,'admitted':ok,'mock_launches':spawned,'physical_launches':0})
assert not base.base.classify_process({'pid':1,'ppid':0,'start_ticks':1,'state':'S','exe':'/usr/bin/node','argv':['metadata-reader','chrome','runner.py']})
print(json.dumps({'cases':cases,'NN':0,'physical_browser':0}))
