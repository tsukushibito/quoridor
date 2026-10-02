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

# Exercise actual scan error handling with a tiny synthetic proc view, not only decision symbols.
from pathlib import Path
import tempfile
from admission import scan_processes
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);p=root/'901';p.mkdir()
 fields=['S','1','901']+['0']*16+['123','0','1']
 (p/'stat').write_text('901 (dummy) '+' '.join(fields))
 (p/'cmdline').write_bytes(b'')
 try:scan_processes(proc=root)
 except RuntimeError as error:assert 'ADMISSION_READ_ERROR' in str(error)
 else:raise AssertionError('LIVE_EMPTY_COMMAND_ALLOWED')
 (p/'cmdline').write_bytes(b'node\x00metadata-reader.cjs\x00')
 assert scan_processes(proc=root)==[]
 (p/'cmdline').write_bytes(b'chrome\x00--type=renderer\x00')
 assert len(scan_processes(proc=root))==1
 (p/'stat').write_text('malformed')
 try:scan_processes(proc=root)
 except RuntimeError as error:assert 'ADMISSION_READ_ERROR' in str(error)
 else:raise AssertionError('MALFORMED_PROC_ALLOWED')
print('actual proc scan: live unknown/malformed reject, metadata nonheavy, renderer heavy; no child launch')
