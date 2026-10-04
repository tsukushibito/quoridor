"""Exactly one fixed four-root native search job after parity PASS."""
from pathlib import Path
import argparse,hashlib,json,subprocess
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-native-connection';T=R/'tools/ai-sigma-frame18-native-connection'
p=argparse.ArgumentParser();p.add_argument('--settings');a=p.parse_args();s=json.loads(Path(a.settings).read_text())
for p,h in s['sources'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
assert json.loads((D/'parity-result.json').read_text())['PASS'];assert not(D/'search-result.json').exists()
subprocess.run(['/home/vscode/.local/bin/node','--max-old-space-size=512',str(T/'search.cjs'),str(D/'weight-manifest.json'),str(D/'search-result.json')],check=True)
v=json.loads((D/'search-result.json').read_text());assert v['samples']<=s['sample_upper']
