"""Offline private baseline and measurement ABI build, immutable module untouched."""
import os,json,subprocess,pathlib,hashlib,datetime,shutil
TOOL=pathlib.Path(__file__).resolve().parent;ROOT=TOOL.parents[1]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/DEEP-NODE-COMPARISON'
os.environ.update(CARGO_HOME='/home/vscode/.cache/inference/research/ai-sigma/ort-search/cargo-home',CARGO_TARGET_DIR=str(OUT/'build/target'),CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0')
(OUT/'build').mkdir(exist_ok=True);rows=[]
for variant in ['baseline','trace']:
    os.environ['CARGO_TARGET_DIR']=str(OUT/'build'/('target-'+variant))
    cmd=['cargo','build','--release','--offline','--locked','--target','wasm32-unknown-unknown','--lib','--manifest-path',str(TOOL/variant/'Cargo.toml')]
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();subprocess.run(cmd,check=True)
    source=pathlib.Path(os.environ['CARGO_TARGET_DIR'])/'wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm'
    dest=OUT/'build'/f'{variant}.wasm';shutil.copyfile(source,dest)
    rows.append({'variant':variant,'command':cmd,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bytes':dest.stat().st_size,'SHA256':hashlib.sha256(dest.read_bytes()).hexdigest()})
original=ROOT/'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm'
(OUT/'build-results-r2.json').write_text(json.dumps({'variants':rows,'immutable_SHA256':hashlib.sha256(original.read_bytes()).hexdigest(),'baseline_byte_equal':(OUT/'build/baseline.wasm').read_bytes()==original.read_bytes(),'RUSTFLAGS':os.environ.get('RUSTFLAGS'),'toolchain':subprocess.check_output(['rustc','--version']).decode().strip()},indent=2)+'\n')
print(json.dumps(rows))
