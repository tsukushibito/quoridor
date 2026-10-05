from pathlib import Path
import json,hashlib,datetime
T=Path(__file__).resolve().parent;A=T.parents[1]/'.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-ENTRY-REPAIR'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[{'path':str(p),'sha256':sha(p)} for p in sorted(T.iterdir()) if p.is_file()]
inputs=json.loads((A/'input-before.json').read_text())['checks']
for x in inputs:assert sha(Path(x['path']))==x['sha256'],x['path']
r={'issue':'quoridor-4lc.68','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_go':False,'entry_ready':False,'checks':checks+inputs,'original_expected_bytes_retained':True}
data=json.dumps(r,indent=2)+'\n';digest=hashlib.sha256(data.encode()).hexdigest();(A/('entry-manifest-'+digest+'.json')).write_text(data);(A/'entry-manifest.json').write_text(data)
print(json.dumps({'source_count':len(checks),'original_inputs':len(inputs),'manifest_sha256':sha(A/'entry-manifest.json')}))
