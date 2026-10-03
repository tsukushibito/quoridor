import json,hashlib,datetime,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';D=R/'research-data/ai-sigma/151-sigma-web-port';name=sys.argv[1];P=O/'runs';p=json.loads((P/(name+'.process.json')).read_text());v=P/name
ids=p['tracked']+[{'pid':p['runner_pid'],'start_ticks':p['runner_starttick']}];same=[]
for x in ids:
 try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(s[19])==x['start_ticks']:same.append(x)
files={n:json.loads((v/(n+'.json')).read_text()) if (v/(n+'.json')).exists() else {'missing':True} for n in ['summary','finally-model-drop','main-timers-stop','monitor-callback-stop','pause-monitor-stop','outer-controlled-stop']}
inner=files.pop('outer-controlled-stop');r={'issue':'quoridor-4lc.151','run':name,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'start':p['start'],'end':p['end'],'exit':p['exit'],'stop_reason':p['stop_reason'],'inner_controlled':{k:inner.get(k) for k in ['remaining_pids','forced','graceful_error','waited','registration_ack','registered']},'inner_proof_path':str(v/'outer-controlled-stop.json'),'outer_ownedwait_returned':True,'outer_remaining':p['remaining'],'outer_unknown':p['unknown_adopted'],'current_sameidentity':same,'identity_count':len(ids),'peak_current_RSS':p['peak_group_plus_runner_RSS'],'retained_current':p['final_allocated_bytes'],'source_launch_hash':p['runner_sha256'],'source_current_hash':hashlib.sha256(Path(__file__).with_name('runner.py').read_bytes()).hexdigest(),'files':files,'natural_allperiod_allhost_not_asserted':True}
assert not same and not p['remaining'] and not p['unknown_adopted'];(D/(name+'-stop.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['run','end','exit','outer_remaining','outer_unknown','identity_count']}))
