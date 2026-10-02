"""Preserve stopped browser results, report them, and admit the next registered pair."""
import datetime,hashlib,io,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX'
DATA=ROOT/'research-data/ai-sigma/119-diverse-prefix'
pair=int(sys.argv[1]);run=f'prefix119-pair{pair}-r1'
s=json.loads((DATA/(run+'.summary.json')).read_text())
assert not s['primary'] and not s['secondary'] and not s['process']['remaining'] and not s['process']['unknown'],'NOT_SAFE_TO_ADVANCE'
paths=[str(p.relative_to(ROOT)) for p in DATA.glob(run+'.*')]
env=os.environ.copy();env['SIGMA_COMMIT_MESSAGE']=f'research117: preserve registered pair{pair}, all outcomes and stop records'
subprocess.run(['bash',str(ROOT/'tools/ai-sigma-diverse-prefix/commit-own.sh'),*paths],cwd=ROOT,env=env,check=True)
manifest=json.loads((DATA/(run+'.manifest.json')).read_text())
blob=subprocess.check_output(['git','show','HEAD:research-data/ai-sigma/119-diverse-prefix/'+run+'.tar.gz'],cwd=ROOT)
assert hashlib.sha256(blob).hexdigest()==manifest['SHA256']
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
 for member in manifest['members']:
  assert hashlib.sha256(tar.extractfile(member['path']).read()).hexdigest()==member['SHA256']
# Only our unused expanded duplicate is removed; process metadata stays for cumulative budgets.
(OUT/'runs'/(run+'.game-count.json')).write_text(json.dumps({'run':run,'games_started':s['games_started'],'public':s['public'],'stopped':True},indent=2)+'\n')
shutil.rmtree(OUT/'runs'/run)
for suffix in ['log','monitor.jsonl','owned-ledger.jsonl']:
 p=OUT/'runs'/(run+'.'+suffix)
 if p.exists():p.unlink()
(OUT/f'pair{pair}-Git-restore-cleanup.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':run,'archive_SHA':manifest['SHA256'],'Git_stream_restore':True,'expanded_duplicate_removed':True,'process_metadata_retained':True},indent=2)+'\n')
report=OUT/f'pair{pair}-report.md'
report.write_text(f"EXPERIMENT_PAIR .117 / pair{pair}\n{json.dumps(s['games'],ensure_ascii=False)}\nWDL {s['WDL']}; public {s['public']}; startupNN {s['startup_NN']} separate; handNN {s['hand_NN']}. primary/secondary0, both models stopped, outer remaining/unknown0. RSSpeak {s['process']['RSS_peak']}B. All turns and stop metadata saved in research Git archive SHA {manifest['SHA256']}; stream restoration verified. Formal fairness/NI/old WDL integration0.\n")
if pair%2==0:
 subprocess.run(['bash','/workspaces/quoridor/scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str(report)],cwd=ROOT,check=True)
if pair==8:sys.exit(0)
