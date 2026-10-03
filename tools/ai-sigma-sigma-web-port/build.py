import os,sys,json,subprocess,pathlib,hashlib,datetime,shutil
T=pathlib.Path(__file__).parent;R=T.parents[1];O=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';target=O/'build/target';target.mkdir(parents=True,exist_ok=True)
os.environ.update(CARGO_HOME='/home/vscode/.cache/inference/research/ai-sigma/ort-search/cargo-home',CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0')
cmd=['cargo','build','--release','--offline','--locked','--target','wasm32-unknown-unknown','--lib','--manifest-path',str(T/'private/Cargo.toml')]
a=datetime.datetime.now(datetime.timezone.utc).isoformat();subprocess.run(cmd,check=True);binary=target/'wasm32-unknown-unknown/release/ai_sigma_ort_search.wasm';dest=O/'build/faithful.wasm';shutil.copyfile(binary,dest)
r={'command':cmd,'start':a,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'SHA256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'rustc':subprocess.check_output(['rustc','--version']).decode().strip(),'cargo':subprocess.check_output(['cargo','--version']).decode().strip(),'RUSTFLAGS':os.getenv('RUSTFLAGS'),'CARGO_TARGET_DIR':str(target),'source':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (T/'private').rglob('*') if p.is_file()}}
(O/'build/build-binding.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
