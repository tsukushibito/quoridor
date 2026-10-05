import subprocess,json,pathlib
p=subprocess.run(['cargo','test','--manifest-path','../../Cargo.toml','--locked','--offline','-p','quoridor-core','-p','quoridor-ai','--no-default-features','--release','--no-run','--message-format=json'],stdout=subprocess.PIPE,check=True,text=True)
paths=[]
for line in p.stdout.splitlines():
 try:v=json.loads(line)
 except ValueError:print(line);continue
 if v.get('reason')=='compiler-artifact' and v.get('profile',{}).get('test') and v.get('executable'):paths.append(v['executable'])
pathlib.Path('../../.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/standard-test-binaries.json').write_text(json.dumps(paths,indent=2));print('standard test executables',len(paths))
