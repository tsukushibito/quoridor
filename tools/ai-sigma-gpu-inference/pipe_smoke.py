"""NN0 stdio roundtrip, synthetic output; not Rust/ORT throughput."""
import os, sys, json, time, subprocess, select, statistics
from pathlib import Path
D=Path('research-data/ai-sigma/174-gpu-inference')
if '--echo' in sys.argv:
    print('READY',flush=True)
    for line in sys.stdin:
        r=json.loads(line);assert len(r['features_bits'])==648
        print(json.dumps({'synthetic':True,'generation':r['generation'],'token':r['token'],'logits':[0.0]*136,'value':0.0},separators=(',',':')),flush=True)
    sys.exit(0)
a=json.loads((D/'inputs.json').read_text())['inputs'][0]['features_bits']
t=time.perf_counter();child=subprocess.Popen([sys.executable,'-B',__file__,'--echo'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
pid=child.pid;starttick=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
try:
 assert select.select([child.stdout],[],[],2)[0] and child.stdout.readline().strip()=='READY'
 startup=time.perf_counter()-t;values=[]
 for i in range(9):
  r={'generation':1,'token':i,'features_bits':a};wire=json.dumps(r,separators=(',',':'))+'\n';t=time.perf_counter_ns()
  child.stdin.write(wire);child.stdin.flush();assert select.select([child.stdout],[],[],1)[0]
  answer=child.stdout.readline();reply=json.loads(answer);assert reply['synthetic'] and reply['token']==i and len(reply['logits'])==136
  elapsed=(time.perf_counter_ns()-t)/1e6
  if i:values.append(elapsed)
 child.stdin.close();child.wait(timeout=2);assert child.returncode==0,child.stderr.read()
 out={'kind':'NN0 synthetic JSON stdio roundtrip','CPU_affinity':sorted(os.sched_getaffinity(0)),'child_pid':pid,'child_starttick':starttick,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'child_waited_exit':child.returncode,'child_current_exact_identity_present':False,'startup_s':startup,'warmup':1,'steady_roundtrip_ms':values,'median_ms':statistics.median(values),'request_bytes':len(wire.encode()),'reply_bytes':len(answer.encode()),'NN':0,'actual_native_adapter_throughput_claim':False}
 (D/'NN0-stdio.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
finally:
 if child.poll() is None:child.kill();child.wait(timeout=2)
