import subprocess
for cmd in [['cargo','fmt','--check'],['cargo','clippy','--release','--offline','--locked','--all-targets','--all-features','--','-D','warnings'],['cargo','test','--release','--offline','--locked','--lib','--no-run'],['cargo','build','--release','--offline','--locked','--target','wasm32-unknown-unknown','--lib']]:subprocess.run(cmd,check=True)
