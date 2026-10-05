import os,json,subprocess,pathlib,hashlib,datetime,shutil
TOOL=pathlib.Path(__file__).resolve().parent
ROOT=TOOL.parents[1];OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/C-FACTOR-BROWSER'
os.environ.update(CARGO_HOME='/home/vscode/.cache/inference/research/ai-sigma/ort-search/cargo-home',CARGO_TARGET_DIR=str(OUT/'build/target'),CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0')
rows=[]
for variant in ['baseline','c1']:
 os.environ['CARGO_TARGET_DIR']=str(OUT/'build'/('target' if variant=='baseline' else 'target-c1'))
 command=['cargo','build','--release','--offline','--locked','--target','wasm32-unknown-unknown','--lib','--manifest-path',str(TOOL/variant/'Cargo.toml')]
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();subprocess.run(command,check=True)
 source=pathlib.Path(os.environ['CARGO_TARGET_DIR'])/'wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm';dest=OUT/'build'/f'{variant}.wasm';shutil.copyfile(source,dest)
 rows.append({'variant':variant,'command':command,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
(OUT/'build-results.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
