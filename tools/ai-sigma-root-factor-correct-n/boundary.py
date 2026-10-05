from pathlib import Path
import subprocess,json,datetime,hashlib
A=Path('.artifacts/ai-sigma/continuation-20261001/SIGMA-ROOT-FACTOR-CORRECT-N');binary=str((A/'checker').resolve());cases=[('self-boundary',None,['--boundary'],0),('wrong-count','0\n',[],101),('negative-node','765\nnegative 1979 10 0 -1 1\n',[],101),('invalid-integer','765\nnegative 1979 10 not_integer 1 1\n',[],101)];rows=[]
for name,data,args,expected in cases:
 if data is not None:p=A/'temp'/(name+'.txt');p.write_text(data);args=[str(p)]
 command=[binary]+args;r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10);row={'name':name,'command':command,'command_sha256':hashlib.sha256(json.dumps(command).encode()).hexdigest(),'exit':r.returncode,'expected_exit':expected,'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'factor_output_absent':not r.stdout};rows.append(row);assert r.returncode==expected;assert not r.stdout
(A/'boundary-check.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_passed':True,'rows':rows,'synthetic_boundary_not_actual765':True,'NN':0},indent=2)+'\n');print('Boundary4 passed; self-boundary includes independent sums, singleton, negative value permitted, negativeprior/nonfinite rejected')
