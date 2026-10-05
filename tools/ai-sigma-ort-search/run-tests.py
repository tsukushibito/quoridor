import pathlib,json,subprocess
run=pathlib.Path('../../.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH')
for binary in json.loads((run/'standard-test-binaries.json').read_text()):subprocess.run([binary,'--test-threads=1'],cwd='../..',check=True)
print('all standard feature-off core/ai tests passed CPU2')
