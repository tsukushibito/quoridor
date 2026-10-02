from admission import classify_process,decide
base={'pid':100,'ppid':90,'start_ticks':123,'state':'R','exe':'/bin/bash','argv':['-c','python3 runner.py --config text']}
assert not classify_process(base)
assert not classify_process(base|{'exe':'/usr/bin/node','argv':['metadata-reader.cjs']})
assert classify_process(base|{'exe':'/bin/chrome','argv':['--type=renderer']})
assert classify_process(base|{'exe':'python3','argv':['-B','/owned/runner.py','--config','x']})
for heavy,previous,error in [([base],[],None),([],[{'remaining':[base],'unknown_adopted':[]}],None),([],[], 'ADMISSION_READ_ERROR'),([],[], 'ADMISSION_READ_TIMEOUT'),([],[], 'OWNER_UNKNOWN')]:
 launches=0
 try:
  decide(heavy,previous,error);launches+=1
 except RuntimeError:pass
 assert launches==0
assert decide([], [{'remaining':[],'unknown_adopted':[]}])
print('actual argv heavy / metadata / parent shell / read error / timeout / ownership / stop-unconfirmed: launch0 cases pass, NN0')
