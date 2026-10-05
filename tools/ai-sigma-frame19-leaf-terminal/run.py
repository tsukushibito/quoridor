from pathlib import Path
import json,subprocess,sys
c=json.loads(Path(sys.argv[1]).read_text());T=Path(__file__).parent
subprocess.run(['/home/vscode/.local/bin/node',str(T/'fixtures.cjs'),sys.argv[1]],check=True)
subprocess.run(['/home/vscode/.local/bin/node',str(T/'profile.cjs'),sys.argv[1]],check=True)
