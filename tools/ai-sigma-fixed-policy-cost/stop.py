import pathlib,json,hashlib,datetime
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/137-fixed-policy-cost';O=R/'.artifacts/ai-sigma/resume-20261002/FIXED-POLICY-COST';runs=O/'runs'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
processes=[load(p) for p in runs.glob('cost137-*.process.json')];ids={}
for d in processes:
 assert not d['remaining'] and not d['unknown_adopted']
 for i in d['tracked']:ids[(i['pid'],i['start_ticks'])]={'pid':i['pid'],'start_ticks':i['start_ticks']}
 for prefix in ['runner','child']:ids[(d[prefix+'_pid'],d[prefix+'_starttick'])]={'pid':d[prefix+'_pid'],'start_ticks':d[prefix+'_starttick']}
same=[]
for i in ids.values():
 try:f=pathlib.Path(f"/proc/{i['pid']}/stat").read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(f[19])==i['start_ticks']:same.append(i)
assert not same
rd=runs/'cost137-r2';model=load(rd/'finally-model-drop.json');timers=load(rd/'main-timers-stop.json');inner=load(rd/'outer-controlled-stop.json');monitor=load(rd/'pause-monitor-stop.json');result=load(rd/'browser-result.json')
assert model['handles']==model['activeNN']==timers['main_timers']==0 and not timers['pending_messages']
assert all(not any(r['stop']['stop'][k] for k in ['handles','activeNN','live_searches','active']) for r in result['rows'])
before=load(D/'source-before-r2.json');after={p:sha(R/p) for p in before};assert before==after
s={'issue':'quoridor-4lc.137','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'last_heavy_end':next(x['end'] for x in processes if x['phase']=='cost'),'jobs':[{k:x[k] for k in ['name','phase','start','end','exit','stop_reason','remaining','unknown_adopted','peak_group_plus_runner_RSS']} for x in processes],'Model2_drop':model,'search_ACK_zero':len(result['rows']),'main_timers':timers,'monitor_callback_stop':True,'monitor_state':monitor['state'],'inner_controlled':inner,'outer_ownedwait_remainingunknown0':True,'identity_count':len(ids),'identities':list(ids.values()),'current_same_identity':same,'current_absence_not_natural_allperiod':True,'measured_source_before_after_exact':True,'source_hashafter':after,'scientific_run_stopped':True,'report_preparation_source_still_active':True,'management_short_command_PID_RSS_fullperiod_not_recorded':True}
(D/'runtime-stopped-early.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({'stop_SHA':sha(D/'runtime-stopped-early.json'),'identities':len(ids),'heavy_end':s['last_heavy_end'],'inner_forced':inner['forced'],'outer_remainingunknown':0}))
