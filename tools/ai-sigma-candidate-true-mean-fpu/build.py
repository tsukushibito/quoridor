import os,sys,json,subprocess,pathlib,hashlib,datetime,shutil
T=pathlib.Path(__file__).parent;R=T.parents[1];O=R/'.artifacts/ai-sigma/resume-20261002/CANDIDATE-TRUE-MEAN-FPU';c=json.loads(pathlib.Path(sys.argv[2]).read_text());variant=c['variant']
assert variant in ['q0','fpu'];target=O/'build'/('target-'+variant);target.mkdir(parents=True,exist_ok=True)
os.environ.update(CARGO_HOME='/home/vscode/.cache/inference/research/ai-sigma/ort-search/cargo-home',CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0')
cmd=['cargo','build','--release','--offline','--locked','--target','wasm32-unknown-unknown','--lib','--manifest-path',str(T/'private/Cargo.toml')]
if variant=='fpu':cmd+=['--features','true-mean-fpu']
a=datetime.datetime.now(datetime.timezone.utc).isoformat();subprocess.run(cmd,check=True);binary=target/'wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm';dest=O/'build'/f'{variant}.wasm';shutil.copyfile(binary,dest)
r={'variant':variant,'command':cmd,'start':a,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'SHA256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'rustc':subprocess.check_output(['rustc','--version']).decode().strip(),'cargo':subprocess.check_output(['cargo','--version']).decode().strip(),'RUSTFLAGS':os.getenv('RUSTFLAGS'),'CARGO_TARGET_DIR':str(target),'source':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (T/'private').rglob('*') if p.is_file()}}
(O/f'build-{variant}.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
