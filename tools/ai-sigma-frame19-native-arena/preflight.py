from pathlib import Path
import subprocess,json,sys,time
c=json.loads(Path(sys.argv[1]).read_text());T=Path(__file__).parent;st=time.monotonic()
subprocess.run(['/home/vscode/.local/bin/node',str(T/'clock-fixture.cjs'),c['clock_output']],check=True)
subprocess.run(['/home/vscode/.local/bin/node',str(T/'bench.cjs'),sys.argv[1]],check=True)
print(json.dumps({'preflight_and_bench_wall_s':time.monotonic()-st,'science_runner_completed':True}))
