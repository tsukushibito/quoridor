"""Current owned storage plus unique Git, conservative remaining forecast."""
import datetime,json,subprocess
from pathlib import Path
D=Path('research-data/ai-sigma/frame15-learning-diagnostic');T=Path('tools/ai-sigma-learning-diagnostic');REPORT=Path('docs/reports/ai-sigma-hypothesis-learning-diagnostic.md')
objects=set()
for p in D.glob('Git-*.json'):objects.update(json.loads(p.read_text()).get('objects',[]))
gitdir=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],text=True).strip())
unique=0
for o in objects:
 p=gitdir/'objects'/o[:2]/o[2:]
 unique+=p.stat().st_size if p.is_file()else int(subprocess.check_output(['git','cat-file','-s',o]))
files=[p for root in [D,T]for p in root.rglob('*')if p.is_file()and '__pycache__'not in p.parts]
for p in Path('models/experiments/nnue').glob('frame15-learning-diagnostic-*'):files.extend(q for q in p.rglob('*')if q.is_file())
files.append(REPORT);current=sum(p.stat().st_size for p in files)
remaining=400000;forecast=current+unique+remaining
assert forecast<6291456,(current,unique,forecast)
r={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'current_owned_files_B':current,'unique_Git_B':unique,'remaining_Git_tmp_metadata_forecast_B':remaining,'forecast_B':forecast,'guard_B':6291456,'reservation_B':8388608,'shared_conservative_allocation_B':57956426,'shared_guard_B':58720256,'shared_reservation_B':67108864,'parent_addition_B':0,'old_unknown_discount_B':0,'checkpoint_and_archives_both_counted':True}
(D/'final-storage.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
