import json,datetime
from admission import launch_if_allowed
calls=[];valid={'decision':'launch_allowed','remaining_unknown':0,'ownership_confirmed':True,'newjob_deadline':'2026-10-02T19:48:05.626296+00:00'}
checks=[]
for name,change in [('false',{'decision':False}),('unknown',{'remaining_unknown':1}),('readerror',{'decision':'readerror'}),('owner',{'ownership_confirmed':False}),('deadline',{'newjob_deadline':'2020-01-01T00:00:00+00:00'})]:
 try:launch_if_allowed({**valid,**change},lambda:calls.append(name))
 except (RuntimeError,KeyError):checks.append(name)
 else:raise AssertionError(name)
assert not calls
print(json.dumps({'mock':True,'spawn0':checks}))
