import datetime, hashlib, itertools, json, math, os, pathlib, statistics, struct, subprocess, tarfile
R = pathlib.Path(__file__).resolve().parents[2]
D = R/'research-data/ai-sigma/138-fixed-cost-saved-independent'
P = R/'research-data/ai-sigma/137-fixed-policy-cost'
checks = []
refs = []
def verify(name, condition):
    checks.append({'check': name, 'pass': bool(condition)})
def digest(b): return hashlib.sha256(b).hexdigest()
def fixed(name, expected=None, git='437f401fd89cb70ec8ff3136e09dea497f7c2cd7'):
    b=(P/name).read_bytes()
    if expected: verify('SHA '+name, digest(b)==expected)
    blob=subprocess.check_output(['git','show',git+':'+str((P/name).relative_to(R))])
    verify('Gitblob '+name,blob==b)
    refs.append({'path':str((P/name).relative_to(R)), 'SHA256':digest(b),'Git':git})
    return json.loads(b)
manifest=fixed('archive-manifest.json')
archive=P/'all-runs-failures.tar.gz'
verify('archive SHA',digest(archive.read_bytes())=='7898f84d2d0c76b371665a71af051952cedc888d2dc7522293649e34539cacb7')
refs.append({'path':str(archive.relative_to(R)), 'SHA256':digest(archive.read_bytes())})
members={m['path']:m for m in manifest['members']}
a=tarfile.open(archive)
def raw(name, lines=False):
    b=a.extractfile(name).read(); m=members[name]
    verify('member '+name,len(b)==m['bytes'] and digest(b)==m['SHA256'])
    refs.append({'member':name, 'SHA256':digest(b),'bytes':len(b)})
    return [json.loads(s) for s in b.splitlines()] if lines else json.loads(b)
handoff=fixed('handoff-summary.json','1a82c4ec3f1c4bf6e80ac917c76a36d7e2bbd8af196a4456f1f4eb3c789f4c7a','4635ab3')
stop=fixed('runtime-source-stopped-before-report.json','79ea43cea782575b004b37561f04267448f375a34b030fbc094362162def240d')
state=fixed('fixed-input.json'); plan=fixed('preregister.json'); owner=fixed('analysis.json')
data=raw('runs/cost137-r2/browser-result.json'); thread=raw('runs/cost137-r2.threads.json')
monitor=raw('runs/cost137-r2.monitor.jsonl',True); process=raw('runs/cost137-r2.process.json')
endclock=raw('runs/cost137-r2/clock-end.json')
drop=raw('runs/cost137-r2/finally-model-drop.json'); timers=raw('runs/cost137-r2/main-timers-stop.json')
load=raw('runs/cost137-r2/model-load.json'); bindings=raw('runs/cost137-r2/source-bindings.json')
outer=raw('runs/cost137-r2.owned-ack.json'); inner=raw('runs/cost137-r2/outer-controlled-stop.json')
callback=raw('runs/cost137-r2/pause-monitor-stop.json')
failures=fixed('failures.json'); admission=raw('runs/cost137-r1.admission-failure.json')
rows=data['rows']; verify('fixed four attempts',len(rows)==len(data['attempts'])==4 and [r['spec']['cost_sample'] for r in rows]==['warm','sample1','sample2','sample3'])
verify('state prefix16 P1',len(state['identity']['prefix'])==len(state['identity']['legal_prefix'])==state['totalply']==16 and state['physical_side']==1)
def clocks(c):
    lo=max(s['worker_ms']-s['end_ms']-.1 for s in c['samples'])
    hi=min(s['worker_ms']-s['start_ms']+.1 for s in c['samples'])
    verify('clock calibration',lo==c['lo_ms'] and hi==c['hi_ms'] and lo<=hi and (lo+hi)/2==c['mid_ms'])
    return lo,hi
def finite(x):
    if isinstance(x,(int,float)): return math.isfinite(x)
    if isinstance(x,list): return all(finite(v) for v in x)
    if isinstance(x,dict): return all(finite(v) for v in x.values())
    return True
def action_of(body):
    z=body['action']
    if z['type']=='wall': return 81+z['y']*8+z['x']+(64 if z['orientation']=='v' else 0)
    raise ValueError('Unexpected action kind: keep unresolved')
sample_results=[]; series=[]
for r in rows:
    id=r['identity']; response=r['response']; pub=r['diagnostic']['sab_publications']; nn=r['diagnostic']['NN_control_events']; low,high=clocks(r['worker_clock'])
    verify('finite raw row',finite(r)); verify('same fixed identity input',all(id[k]==state['identity'][k] for k in ['key','history','prefix','legal_prefix','model']))
    numeric=r['diagnostic']['numeric'][0]
    verify('root input/137 correspondence',numeric==state['numeric'] and len(numeric['features_bits'])==648 and len(numeric['policy_logits'])==136 and -1<=numeric['value']<=1)
    verify('features bits f32 finite',all(math.isfinite(struct.unpack('<f',struct.pack('<I',v))[0]) for v in numeric['features_bits']))
    verify('accepted sequence/K complete', [p['sequence'] for p in pub]==[p['completed_backup'] for p in pub]==list(range(1,len(pub)+1)))
    for p in pub:
        k=p['completed_backup']; edges=p['root_edges']; n=sum(e[2] for e in edges)
        verify('reference root/edge/loop/NN',p['rootN']==k and p['loop_simulations']==n==p['edge_sum']==k-1 and p['cp_NN_calls']==k)
        verify('Action first max visit',p['action']==max(edges,key=lambda e:e[2])[0])
        verify('edge stats finite/prior/visits',finite(edges) and all(0<=e[1]<=1 and isinstance(e[2],int) and e[2]>=0 for e in edges) and abs(sum(e[1] for e in edges)-1)<1e-12)
    cp=r['adopted_stats']; b=response['body']; generation=id['generation']
    verify('adoption last accepted/body sequence',cp==pub[-1] and response['adopt_checkpoint']['sequence']==b['sequence']==cp['sequence'] and action_of(b)==cp['action'])
    verify('UTF8 unchanged serialized body',json.loads(response['body_serialized'])==b and len(response['body_serialized'].encode())==response['bytes'] and r['postpublic_immutable'])
    verify('generation binding',b['generation']==generation and b['request_id']==id['request_id'] and all(n['generation']==generation and n['request_id']==id['request_id'] for n in nn))
    verify('T500/402/411',id['deadline_ms']-id['t0_ms']==500 and id['commit_cutoff_ms']-id['t0_ms']==402 and response['planned_ms']-id['t0_ms']==411)
    verify('public stamp and eligibility',response['stamp_ms']-id['t0_ms']==response['public_elapsed_ms'] and response['stamp_ms']<=id['deadline_ms'])
    ve=r['diagnostic']['validation_events']; accepted=[v for v in ve if v['accepted']]; rejected=[v for v in ve if not v['accepted']]
    verify('accepted private cache before early cutoff',[v['sequence'] for v in accepted]==[p['sequence'] for p in pub] and all(v['validated_cache_ms']<=id['commit_cutoff_ms']+low for v in accepted))
    sp=r['cost_spans']; dur=[n['return_ms']-n['start_ms'] for n in nn]
    at=r['stop']['stop']['at_ms']; ack=r['stop']['main_received_ms']
    verify('search ACK zero', all(r['stop']['stop'][k]==0 for k in ['handles','activeNN','live_searches']))
    verify('ACK actual main',ack-id['t0_ms']==r['ACK_wall_ms'])
    verify('old zero before own t0',sp['both_previous_zero_wait_end_ms']<=id['t0_ms'])
    finish=[v for v in r['diagnostic']['result']['spans'] if v['kind']=='finish']
    sample_results.append({'sample':r['spec']['cost_sample'],'eligible_K':cp['completed_backup'],'Action':cp['action'],'rootN':cp['rootN'],'edge_sum':sum(e[2] for e in cp['root_edges']),'API_calls':len(nn),'discard':sum(n['result_discarded'] for n in nn),'kernel_finish_markers':len(finish),'rejected':rejected,'rejected_CP_transport_full_body_missing':bool(rejected),'public_ms':response['stamp_ms']-id['t0_ms'],'timer_late_ms':response['timer_ms']-response['planned_ms'],'APIawait_median':statistics.median(dur),'first_APIawait':dur[0],'ACKwall_ms':ack-id['t0_ms'],'Workerstop_main_lower_ms':at-high-id['t0_ms'],'Workerstop_main_upper_ms':at-low-id['t0_ms'],'post_public_API_definite':sum(n['session_run_start_ms']-high>response['stamp_ms'] for n in nn),'post_public_API_possible':sum(n['session_run_start_ms']-low>response['stamp_ms'] for n in nn),'API_overlap_midpoint_ms':sum(max(0,n['return_ms']-max(n['start_ms'],response['stamp_ms']+r['worker_clock']['mid_ms'])) for n in nn),'public_to_both_zero_ms':sp['both_zero_after_ms']-sp['public_return_ms'],'rootFinished_missing':r['diagnostic']['result'].get('rootFinished') is None})
    series.append({p['completed_backup']:p for p in pub})
comparisons=[]
for i,j in itertools.combinations(range(4),2):
    common=sorted(series[i].keys()&series[j].keys()); comparisons.append({'samples':[i,j],'exact_K':common,'Action_same':all(series[i][k]['action']==series[j][k]['action'] for k in common),'root_edges_exact':all(series[i][k]['root_edges']==series[j][k]['root_edges'] for k in common)})
saved_comparisons=[]
for i,p in enumerate(series):
    for j,q in enumerate(state['saved_CP_series']):
        q={z['completed_backup']:z for z in q};common=sorted(p.keys()&q.keys())
        saved_comparisons.append({'sample':i,'saved_rep':j,'exact_K':common,'Action_same':all(p[k]['action']==q[k]['action'] for k in common)})
verify('same K across all pairs',all(c['Action_same'] and c['root_edges_exact'] for c in comparisons))
verify('saved exact K actions',all(c['Action_same'] for c in saved_comparisons))
old_members=[]
for ref in state['source_refs']:
    group=ref['archive_member'].split('/')[1]; old_archive=R/'research-data/ai-sigma/134-local-move-quality'/(group+'.tar.gz')
    with tarfile.open(old_archive) as old:
        b=old.extractfile(ref['archive_member']).read()
    verify('old134 required member SHA',digest(b)==ref['SHA256'])
    oldrow=json.loads(b)['rows'][ref['row_index']]
    verify('old134 actual row binding',oldrow['identity']['request_id']==ref['request_id'] and all(oldrow['identity'][k]==state['identity'][k] for k in ['key','history','legal_prefix']) and oldrow['diagnostic']['numeric'][0]==state['numeric'])
    verify('old134 actual CP series',oldrow['diagnostic']['sab_publications']==state['saved_CP_series'][len(old_members)])
    old_members.append({'archive':str(old_archive.relative_to(R)),'member':ref['archive_member'],'SHA256':digest(b),'row_index':ref['row_index']})
verify('actual session2 same policy/model/thread',len(load['players'])==2 and {p['physical_slot'] for p in load['players']}=={'candidate','reference'} and all(p['digest']==state['identity']['model'] and p['threads']==1 and not p['proxy'] and p['policy']=='fixedSigma C1/FPU.2/first/temp0/originalorder' for p in load['players']))
verify('startup6 separate NN',len(data['startup_rows'])==6 and sum(s['NN'] for s in data['startup_rows'])==6)
samples=thread['samples']; verify('TID162 samples',len(samples)==162)
counter_names=['utime_ticks','stime_ticks','runtime_ns','runqueue_ns','timeslices']
def key(t):return (t['pid'],t['pid_start_ticks'],t['TID'],t['tid_start_ticks'])
maps=[{key(t):t for t in s['threads']} for s in samples]
proxy=set((t['pid'],t['pid_start_ticks']) for s in samples for t in s['threads'] if t['pid']==t['TID'] and t['comm'] in ['chrome','chrome_crashpad'])
all_deltas=[]
for i in range(1,len(samples)):
    for k in maps[i-1].keys()&maps[i].keys():
        delta=[maps[i][k][n]-maps[i-1][k][n] for n in counter_names]
        all_deltas.append(delta)
verify('all adjacent common identity monotone',all(min(x)>=0 for x in all_deltas))
widths=[(s['read_end_unix_ns']-s['unix_ns'])/1e6 for s in samples]
verify('sample read width positive',min(widths)>=0)
def interval(start,end):
    indices=[i for i,s in enumerate(samples) if s['unix_ns']/1e6>=start and s['read_end_unix_ns']/1e6<=end]
    if len(indices)<2:return {'supported':False,'inner_samples':len(indices),'missing':'fewer than two inner endpoint samples'}
    i,j=indices[0],indices[-1]; common=maps[i].keys()&maps[j].keys();totals={'chrome':{n:0 for n in counter_names},'other':{n:0 for n in counter_names}}
    for k in common:
        delta={n:maps[j][k][n]-maps[i][k][n] for n in counter_names};verify('interval counters monotone',min(delta.values())>=0)
        bucket=totals['chrome' if k[:2] in proxy else 'other']
        for n,v in delta.items():bucket[n]+=v
    result={'supported':True,'inner_samples':len(indices),'first_sample':i,'last_sample':j,'leading_missing_ms':samples[i]['unix_ns']/1e6-start,'trailing_missing_ms':end-samples[j]['read_end_unix_ns']/1e6,'read_width_ms':[widths[i],widths[j]],'disappeared_endpoint_TIDs':len(maps[i].keys()-maps[j].keys()),'new_endpoint_TIDs':len(maps[j].keys()-maps[i].keys()),'common_TIDs':len(common),'sums_raw':totals}
    for b in totals:
        result[b+'_runtime_ms']=totals[b]['runtime_ns']/1e6;result[b+'_runqueue_TIDsum_ms']=totals[b]['runqueue_ns']/1e6
        result[b+'_tick_CPU_ms']=(totals[b]['utime_ticks']+totals[b]['stime_ticks'])*1000/thread['clock_ticks_per_second']
    return result
cpu=[]
for r,summary,original in zip(rows,sample_results,owner['samples']):
    q=interval(r['cost_markers']['dispatch_ms'],r['response']['stamp_ms']); tail=interval(r['response']['stamp_ms'],r['stop']['main_received_ms']);cpu.append({'sample':summary['sample'],'dispatch_public':q,'public_ACK':tail})
    orig=original['CPU_dispatch_to_public']
    verify('owner inner endpoint arithmetic', all(abs(q[x]-orig[y])<1e-9 for x,y in [('chrome_runtime_ms','Chrome_runtime_ms'),('chrome_runqueue_TIDsum_ms','Chrome_runqueue_TIDsum_ms'),('other_runtime_ms','owned_nonChrome_runtime_ms'),('leading_missing_ms','leading_missing_ms'),('trailing_missing_ms','trailing_missing_ms')]))
for c in endclock.values():
    if isinstance(c,dict) and 'samples' in c:clocks(c)
verify('Model2 drop raw',len(drop['players'])==2 and drop['handles']==drop['activeNN']==0 and all(p['handles']==p['activeNN']==0 for p in drop['players']))
verify('timer message zero',timers['main_timers']==0 and timers['pending_messages']==[])
verify('inner controlled forced wait',inner['forced'] and inner['waited'] and inner['remaining_pids']==0)
verify('outer sole root wait empty',outer['kernel_boundary']['valid'] and outer['kernel_boundary']['sole_explicit_root'] and outer['registered_live']==outer['unknown_adopted']==[] and process['remaining']==process['unknown_adopted']==[])
verify('monitor callbacks timer stop',callback['all_owned_read_callbacks_waited'] and callback['pending_children']==[] and not callback['active_monitor_timer'])
verify('final source stopped',stop['source_write_stopped'] and not stop['report_preparation_source_still_active'])
current=[]; read_errors=[]; boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
verify('same boot',boot==stop['boot'])
for id in stop['identities']:
    try: fields=pathlib.Path('/proc/'+str(id['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
    except FileNotFoundError:continue
    except Exception as e:read_errors.append(str(e));continue
    if int(fields[19])==id['start_ticks']:current.append(id)
verify('74 current same identities absent',len(stop['identities'])==74 and not current and not read_errors)
source_matches=[]
for p,h in stop['source_hashafter_all_own'].items():source_matches.append({'path':p,'match':digest((R/p).read_bytes())==h})
verify('final source hash after',all(x['match'] for x in source_matches))
verify('beforeafter saved claim/source',stop['measured_source_before_after_exact'])
before=fixed('source-before-r2.json')
verify('measured beforeafter hash dictionaries',before==stop['source_hashafter'])
for p in ['tools/ai-sigma-fixed-policy-cost/browser.cjs','tools/ai-sigma-fixed-policy-cost/adapters.cjs','tools/ai-sigma-fixed-policy-cost/cost-main.js']:
    measured=subprocess.check_output(['git','show','451f5007efc6c52f1e3055db2344525bdd6ffee2:'+p]);verify('measured entry Git '+p,digest(measured)==before[p])
cycles=[m['elapsed_seconds']*1000 for m in monitor if m['kind']=='monitor_cycle']
output={'issue':'quoridor-4lc.138','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'fail_count':sum(not c['pass'] for c in checks),'samples':sample_results,'same_exact_K':comparisons,'old_saved_exact_K':saved_comparisons,'TID':{'samples':len(samples),'adjacent_common_deltas':len(all_deltas),'read_errors':sum(len(s['errors']) for s in samples),'read_width_min_median_max_ms':[min(widths),statistics.median(widths),max(widths)],'tick_ms':1000/thread['clock_ticks_per_second'],'intervals':cpu,'exe_at_sample_missing':True,'Worker_NN_TID_binding':None,'guardian_final_CPU_missing':True,'disappeared_final_counter_missing':True,'comm_proxy_whole_process_not_CPU_attribution':True,'runqueue_sum_not_wall':True,'monitor_cycle_wall_median_ms':statistics.median(cycles),'monitor_cycle_wall_sum_ms':sum(cycles)},'stop':{'Model2drop':drop,'search_ACK4':all(all(r['stop']['stop'][k]==0 for k in ['handles','activeNN','live_searches']) for r in rows),'main':timers,'monitor_callback_original':callback,'inner_forced_original':inner,'outerwait_remainingunknown_original':{k:v for k,v in outer.items() if k in ['remaining','unknown','remaining_pids','unknown_adopted']},'74_current':current,'read_errors':read_errors,'source_hashafter_match':source_matches,'current_absence_not_natural_allperiod':True},'refs':refs,'original_failures':failures,'admission_failure_original':admission,'hand_NN':sum(x['API_calls'] for x in sample_results),'startup_NN':len(data['startup_rows']),'session_count':2,'games':0,'new_NN_Chrome':0}
(D/'independent-results.json').write_text(json.dumps(output,indent=2)+'\n')
(D/'old134-required-members.json').write_text(json.dumps(old_members,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'failed':[c for c in checks if not c['pass']],'samples':sample_results,'CPU':cpu,'startup_rows':len(data['startup_rows'])},ensure_ascii=False))
