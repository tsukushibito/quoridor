BASE_SHA='16e373202f4e5c6f231c3b7469f7f9349c0ebdb8d1eeaf4d951c178f9db9e1af'
BUDGET_BLOCK="newprior=[json.loads(p.read_text())for p in(D/'jobs').glob('*/process.json')]+[json.loads(p.read_text())for p in(D/'test-sealed/jobs').glob('*/process.json')]\nspent=sum(p['jobwall_seconds']for p in newprior)\nsamples=sum(p['sample_equivalent'] if p.get('sample_equivalent')is not None else p['NN_cap']for p in newprior)\nassert spent+c['job_seconds']<=5400 and samples+c['NN_cap']<=2200000,'NEW_GEN_BUDGET'\nassert c['max_batch']==8 and c['active_per_worker']==8 and c['NN_cap']<=307200 and c['job_seconds']<=600\nassert hashlib.sha256((R/'tools/ai-sigma-teacher-throughput/codec-control/provider.py').read_bytes()).hexdigest()=='a422650a8cf01b61870c28e800b4595db7e4699166a5b02518ac23e0cdc8666e','UNCHANGED_PROVIDER_PARITY_REUSE'\nstorage=json.loads((D/'storage-admission.json').read_text())\nassert storage['unused_after_reservation_B']>=0\nstageusage=lambda:sum(p.stat().st_size for root in[A,D]for p in root.rglob('*')if p.is_file())\ngitupper=storage['authorizedGit_forecast_B']\nforecast=stageusage()+gitupper+storage['temp_and_residual_forecast_B']+c['job_raw_forecast_B']\nassert forecast<448*1024**2,('NEW_STORAGE_FORECAST',forecast)\noldcurrent=storage['old_scopes_current_B']\n"
# Readonly stopped guardian lifecycle; bounded in-memory task-specific admission patch.
from pathlib import Path
import hashlib
R=Path.cwd()
P=R/'tools/ai-sigma-worker-balance/runner.py'
assert hashlib.sha256(P.read_bytes()).hexdigest()==BASE_SHA
s=P.read_text().replace("225 bounded","228 bounded").replace("tools/ai-sigma-worker-balance","tools/ai-sigma-frame18-data-learning").replace("research-data/ai-sigma/frame18-worker-balance","research-data/ai-sigma/frame18-data-learning").replace('quoridor-4lc.225','quoridor-4lc.228').replace("endswith('.225')","endswith('.228')").replace('2026-10-04T11:15:18Z','2026-10-04T12:50:00Z').replace('2026-10-04T11:25:18Z','2026-10-04T13:05:00Z')
s=s.replace("A=T;O=D","A=T;O=D")
s=s.replace("if sch['owned']is not None:assert c.get('allow_owned_LLM_with_physical_guard')is True,'CURRENT_OWNED_PHYSICAL_POLICY_REQUIRED'","assert sch['owned'] is None,'NATURAL_OWNED_RECALL_REQUIRED_FOR_4CORE_GENERATION'")
a=s.index('newprior=[]');b=s.index("save('admission.json'",a)
s=s[:a]+BUDGET_BLOCK+s[b:]
s=s.replace('224*1024**2','448*1024**2')
exec(compile(s,str(P)+' [228 bounded private admission/lifecycle]','exec'),globals())
