import pathlib,json,subprocess,time
ROOT=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH';binary='/home/vscode/.cache/inference/research/ai-sigma/nn-search/target/release/ai-sigma-nn-search';model=ROOT/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx'
stderr=(RUN/'native-boundary.stderr.log').open('w');p=subprocess.Popen([binary,'serve',str(model)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True);ready=json.loads(p.stdout.readline());assert ready['ready'];rows=[];g=0
try:
 def send(req):
  global g
  g+=1;t0=time.monotonic()*1000;req.update(generation=g,clock_t0_ms=t0,T_ms=500,guard_ms=100);p.stdin.write(json.dumps(req)+'\n');p.stdin.flush();v=json.loads(p.stdout.readline());return {'request_generation':g,'elapsed_ms':time.monotonic()*1000-t0,'payload':v}
 rows.append(send({'prefix':[],'simulations':8,'diagnostic_step_delay_ms':500}));assert rows[-1]['payload']['data']['status']=='timeout'and rows[-1]['payload']['data']['checkpoint']is None and rows[-1]['payload']['data']['overshoot']
 rows.append(send({'prefix':[999]}));assert not rows[-1]['payload']['ok']
 rows.append(send({'prefix':[],'inject_nn_error':True}));assert not rows[-1]['payload']['ok']and rows[-1]['payload']['result_discarded']
 # Old generation invalidated during one synchronous step; retained boundary times in stderr.
 g+=1;old=g;t0=time.monotonic()*1000;req={'prefix':[],'simulations':4096,'max_nodes':512,'max_depth':24,'generation':old,'clock_t0_ms':t0,'T_ms':1000,'guard_ms':100};p.stdin.write(json.dumps(req)+'\n');p.stdin.flush();time.sleep(.002);g+=1;cancel_at=time.monotonic()*1000;p.stdin.write(json.dumps({'kind':'cancel','generation':g})+'\n');p.stdin.flush();cancelled=json.loads(p.stdout.readline());assert not cancelled['ok'];replacement=send({'prefix':[],'simulations':1});assert replacement['payload']['ok'];cancel={'old_generation':old,'cancel_at_ms':cancel_at,'cancelled':cancelled,'replacement':replacement}
finally:p.stdin.close();p.wait(timeout=5);stderr.close()
bad=RUN/'bad-model-bytes.bin';bad.write_bytes(b'bad');negative=subprocess.run([binary,'serve',str(bad)],capture_output=True,text=True);assert negative.returncode==2;error=json.loads(negative.stdout);assert not error['ok'];(RUN/'native-boundary.json').write_text(json.dumps({'ready':ready,'rows':rows,'cancel':cancel,'invalid_model':error,'invalid_model_exit':negative.returncode,'server_exit':p.returncode},indent=2));print(json.dumps({'boundary_timeout':True,'errors':3,'old_rejected':True}))
