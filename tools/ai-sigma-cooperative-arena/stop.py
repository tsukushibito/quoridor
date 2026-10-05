"""Read-only process identity and source checks after owned jobs finish."""
import json,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOOL=Path(__file__).resolve().parent
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA'
label=sys.argv[1]
identity=set();jobs=[]
for path in OUT.glob('*.process.json'):
 record=json.loads(path.read_text())
 jobs.append({k:record.get(k) for k in ['name','start','end','exit','stop_reason','remaining','unknown_adopted','peak_group_plus_runner_RSS','peak_allocated_bytes','assigned_CPU','guardRSS','runner_ru_maxrss_bytes']})
 assert record['remaining']==[] and record['unknown_adopted']==[]
 for row in record.get('tracked',[]):identity.add((row['pid'],row.get('start_ticks',row.get('starttick'))))
 for kind in ['runner','child']:
  if record.get(kind+'_pid'):identity.add((record[kind+'_pid'],record[kind+'_starttick']))
live=[]
for pid,tick in identity:
 try:
  if int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])==tick:live.append({'pid':pid,'starttick':tick})
 except (OSError,ValueError,IndexError):pass
assert not live
before=json.loads((OUT/'headroom-initial.json').read_text())
hashes={name:hashlib.sha256(Path(path).read_bytes()).hexdigest() for name,path in before['input_paths'].items()}
assert hashes==before['input_hashes']
runs=[]
for run in ['initial-pair-r1','asym-pair-r1','jump-pair-r1']:
 base=OUT/run
 summary=json.loads((base/'summary.json').read_text())
 drop=json.loads((base/'backend-stop.json').read_text())
 assert drop['handles']==drop['activeNN']==drop['live_searches']==0 and drop['controlledPID0']
 runs.append({**{k:summary[k] for k in ['run_id','Git','game_starts','turns','public_accepted','budget_breaches','NN_hand','W','D','L','unfinished_games','primary','secondary']},'startup_NN':summary['startup']['root_NN'],'backend_stop':drop,'monitor_stop':json.loads((base/'pause-monitor-stop.json').read_text())})
result={'issue':'quoridor-4lc.103','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'identity_count':len(identity),'recorded_identities':[{'pid':pid,'starttick':tick} for pid,tick in sorted(identity)],'current_live':live,'input_after_hashes':hashes,'own_source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in TOOL.iterdir() if p.is_file()},'jobs':jobs,'runs':runs,'game_cap_reached':sum(r['game_starts'] for r in runs)==6,'further_NN_or_games':False,'forced_and_current_absence_not_natural_or_all_period_proof':True,'formal_fairness':False,'formal_NI':False}
(OUT/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'stop_file':label+'.json','SHA256':hashlib.sha256((OUT/(label+'.json')).read_bytes()).hexdigest(),'identity_count':len(identity),'current_live':live,'game_starts':sum(r['game_starts'] for r in runs),'public':sum(r['turns'] for r in runs),'accepted':sum(r['public_accepted'] for r in runs),'NN_hand':sum(r['NN_hand'] for r in runs),'startup_NN':sum(r['startup_NN'] for r in runs)}))
