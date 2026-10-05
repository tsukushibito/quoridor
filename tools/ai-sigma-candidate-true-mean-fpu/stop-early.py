from pathlib import Path
import json,hashlib,datetime
T=Path(__file__).parent;R=T.parents[1];D=R/'research-data/ai-sigma/140-candidate-true-mean-fpu';O=R/'.artifacts/ai-sigma/resume-20261002/CANDIDATE-TRUE-MEAN-FPU';jobs=[];ids={}
for p in sorted((O/'runs').glob('fpu140-*.process.json')):
 d=json.loads(p.read_text());jobs.append({k:d[k] for k in ['name','phase','start','end','exit','stop_reason','remaining','unknown_adopted','peak_group_plus_runner_RSS']})
 for v in d['tracked']+[{'pid':d['runner_pid'],'start_ticks':d['runner_starttick']}]:ids[(v['pid'],v['start_ticks'])]={'pid':v['pid'],'start_ticks':v['start_ticks']}
for p in (O/'runs').glob('*.owned-ack.json'):
 d=json.loads(p.read_text())
 def visit(v):
  if isinstance(v,dict):
   if 'pid' in v and ('start_ticks' in v or 'starttick' in v):ids[(v['pid'],v.get('start_ticks',v.get('starttick')))]={'pid':v['pid'],'start_ticks':v.get('start_ticks',v.get('starttick'))}
   for x in v.values():visit(x)
  elif isinstance(v,list):
   for x in v:visit(x)
 visit(d)
same=[]
for v in ids.values():
 try:s=Path(f"/proc/{v['pid']}/stat").read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(s[19])==v['start_ticks']:same.append(v)
B=O/'runs/fpu140-mechanism-r1';drop=json.loads((B/'finally-model-drop.json').read_text());timers=json.loads((B/'main-timers-stop.json').read_text());inner=json.loads((B/'outer-controlled-stop.json').read_text());monitor=json.loads((B/'pause-monitor-stop.json').read_text());result=json.loads((B/'browser-result.json').read_text());before=json.loads((D/'source-before.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not same and all(not j['remaining'] and not j['unknown_adopted'] for j in jobs)
assert not drop['handles'] and not drop['activeNN'] and not timers['main_timers'] and not timers['pending_messages']
assert all(not r['zero']['handles'] and not r['zero']['activeNN'] and not r['zero']['active'] for r in result['mean_results'])
own={p:sha(R/p) for p in before['own']};readonly={p:sha(R/p) for p in before['readonly']};assert own==before['own'] and readonly==before['readonly']
s={'issue':'quoridor-4lc.140','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'last_heavy_end':next(j['end'] for j in jobs if j['phase']=='mechanism'),'jobs':jobs,'Model2_drop':drop,'search_zero_receipts':6,'private_ABI_handles_zero_each':True,'main_timers':timers,'monitor_callback_stop':True,'monitor_state':monitor,'inner_controlled':inner,'outer_ownedwait_remainingunknown0':True,'identities':list(ids.values()),'identity_count':len(ids),'current_same_identity':same,'measured_source_before_after_exact':True,'readonly_before_after_exact':True,'source_hashafter':own,'source_write_stopped_measured_code':True,'report_preparation_source_still_active':True,'scientific_run_stopped':True,'quality_started':0,'quality_branch':result['branch'],'current_absence_not_natural_or_allhost_or_fullperiod':True}
(D/'runtime-stopped-early.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({'last_heavy_end':s['last_heavy_end'],'identity_count':len(ids),'current_same_identity':same,'branch':result['branch'],'SHA256':sha(D/'runtime-stopped-early.json')}))
