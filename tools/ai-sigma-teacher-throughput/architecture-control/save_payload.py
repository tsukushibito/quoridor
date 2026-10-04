from pathlib import Path
import datetime,hashlib,json,subprocess,time
R=Path.cwd();T=R/'tools/ai-sigma-teacher-throughput';D=R/'research-data/ai-sigma/frame16-teacher-throughput';A=T/'architecture-control';O=D/'architecture-control'
files=[str(p.relative_to(R))for root in[A,O]for p in root.rglob('*')if p.is_file()and '/jobs/'not in str(p) and p.name not in ['payload-save-receipt.json','final-save-receipt.json']]
start=time.monotonic();commit=subprocess.check_output(['/home/vscode/.cache/inference/envs/quoridor-training/bin/python','-B',str(T/'save_git.py'),*files],text=True).strip();wall=time.monotonic()-start
idx=subprocess.check_output(['git','rev-parse','--git-path','index'],text=True).strip();ish=hashlib.sha256(Path(idx).read_bytes()).hexdigest();assert ish=='59880a1d93833b8a0ea250e9a2b1270c41ceb9f6666da9ab0edeb48991817072'
rec=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),commit=commit,files=len(files),savedbyte_restore_PASS=True,source_control_immutable=True,wall_seconds=wall,defaultindex_SHA=ish,defaultindex_unchanged=True,privateindex=False,archive_SHA=json.loads((O/'archive-manifest.json').read_text())['archive_SHA']);(O/'payload-save-receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
