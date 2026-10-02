"""Preserve stopped browser results, report them, and admit the next registered pair."""
import datetime,hashlib,io,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/CPU-SIGMA-COMPARISON'
DATA=ROOT/'research-data/ai-sigma/117-cpu-sigma-comparison'
pair=int(sys.argv[1]);run=f'cpu117-pair{pair}-r1'
s=json.loads((DATA/(run+'.summary.json')).read_text())
assert not s['primary'] and not s['secondary'] and not s['process']['remaining'] and not s['process']['unknown'],'NOT_SAFE_TO_ADVANCE'
paths=[str(p.relative_to(ROOT)) for p in DATA.glob(run+'.*')]
env=os.environ.copy();env['SIGMA_COMMIT_MESSAGE']=f'research117: preserve registered pair{pair}, all outcomes and stop records'
subprocess.run(['bash',str(ROOT/'tools/ai-sigma-cpu-sigma-frame8/commit-own.sh'),*paths],cwd=ROOT,env=env,check=True)
manifest=json.loads((DATA/(run+'.manifest.json')).read_text())
blob=subprocess.check_output(['git','show','HEAD:research-data/ai-sigma/117-cpu-sigma-comparison/'+run+'.tar.gz'],cwd=ROOT)
assert hashlib.sha256(blob).hexdigest()==manifest['SHA256']
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
 for member in manifest['members']:
  assert hashlib.sha256(tar.extractfile(member['path']).read()).hexdigest()==member['SHA256']
# Only our unused expanded duplicate is removed; process metadata stays for cumulative budgets.
shutil.rmtree(OUT/'runs'/run)
for suffix in ['log','monitor.jsonl','owned-ledger.jsonl']:
 p=OUT/'runs'/(run+'.'+suffix)
 if p.exists():p.unlink()
(OUT/f'pair{pair}-Git-restore-cleanup.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':run,'archive_SHA':manifest['SHA256'],'Git_stream_restore':True,'expanded_duplicate_removed':True,'process_metadata_retained':True},indent=2)+'\n')
report=OUT/f'pair{pair}-report.md'
report.write_text(f"EXPERIMENT_PAIR .117 / pair{pair}\n{json.dumps(s['games'],ensure_ascii=False)}\nWDL {s['WDL']}; public {s['public']}; startupNN {s['startup_NN']} separate; handNN {s['hand_NN']}. primary/secondary0, both models stopped, outer remaining/unknown0. RSSpeak {s['process']['RSS_peak']}B. All turns and stop metadata saved in research Git archive SHA {manifest['SHA256']}; stream restoration verified. Formal fairness/NI/old WDL integration0.\n")
subprocess.run(['bash','/workspaces/quoridor/scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str(report)],cwd=ROOT,check=True)
if pair==6:sys.exit(0)
current_heavy=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  args=(p/'cmdline').read_bytes().split(b'\0'); executable=Path(args[0].decode(errors='replace')).name if args and args[0] else ''; argv=[a.decode(errors='replace') for a in args[1:] if a]
  is_renderer=executable in ['chrome','chromium','chrome-headless-shell'] and any(a=='--type=renderer' for a in argv)
  is_runner=executable.startswith('python') and any(a.endswith('/runner.py') or a=='runner.py' for a in argv)
  is_build=executable=='cargo' and 'build' in argv
  if (is_renderer or is_runner or is_build) and int(p.name)!=os.getpid():current_heavy.append({'pid':int(p.name),'command':cmd})
 except OSError:pass
assert not current_heavy,('OTHER_HEAVY_PRESENT',current_heavy)
allocated=sum(p.stat().st_blocks*512 for base in [OUT,DATA,ROOT/'tools/ai-sigma-cpu-sigma-frame8'] for p in base.rglob('*') if p.is_file())
assert allocated+83886080<117440512,'HEADROOM'
processes=[json.loads(p.read_text()) for p in (OUT/'runs').glob('cpu117-*.process.json')]
heavy=sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in processes if p.get('phase')!='protocol')
assert heavy+400<3600,'HEAVY_BUDGET'
assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-02T12:08:00+00:00'),'INSUFFICIENT_RUN_END_RESERVE'
(OUT/f'pair{pair+1}-admission.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'current_allocated':allocated,'forecast':83886080,'outside_heavy':current_heavy,'heavy_used_seconds':heavy,'remaining_heavy_seconds':3600-heavy,'previous_remaining':s['process']['remaining'],'previous_unknown':s['process']['unknown'],'games_started_total':sum(json.loads(p.read_text()).get('games_started',0) for p in DATA.glob('*.summary.json')),'worst_next_pair_seconds':400},indent=2)+'\n')
