import admission,ast,pathlib
for heavy,error in [([{'pid':1,'exe':'chrome','argv':['--headless']}],False),([],True)]:
 try:admission.decide(heavy,[],error)
 except RuntimeError:pass
 else:raise AssertionError('REJECTION_MISSING')
assert admission.decide([],[]) is True
source=(pathlib.Path(__file__).parent/'runner.py').read_text();assert source.index("assert isinstance(admission,dict)")<source.index('child=subprocess.Popen')
for answer in [False,None,{'decision':'unknown'}]:
 spawned=False
 try:
  assert isinstance(answer,dict) and answer.get('decision')=='launch_allowed'
  spawned=True
 except AssertionError:pass
 assert not spawned
print('false/unknown/readerror rejection: spawn0, real runner assertion before sole Popen')
