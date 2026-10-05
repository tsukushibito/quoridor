import json,pathlib,hashlib,datetime
D=pathlib.Path('research-data/ai-sigma/155-sigma-web-port-games-independent');P=pathlib.Path('.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs');out={'engines':{e:{'requests':0,'API_started':0,'API_returned':0,'discarded':0,'postpublic_start_definite':0,'postcutoff_start_definite':0,'postcutoff_start_possible':0,'returned_afterpublic_definite':0,'ACK_after500':0,'clockbrackets':[],'cache_margin_min':None,'public_margin_min':None} for e in ['candidate','reference']},'exactstore_missing':True,'clock_drift_missing':True,'root_edge_CP_checked':0}
for group in range(1,5):
 p=P/f'port151-stageB-group{group}-r1'
 for f in p.glob('completed-game*.json'):
  a=json.loads(f.read_text())
  for r in a['rows']:
   i=r['identity'];e=i['engine'];d=r['diagnostic'];c=r['adoptedCP'];cp=d['validated_cp'];v=out['engines'][e];w=r['worker_clock'];t=i['t0_ms'];pub=r['response']['stamp_ms'];cut=i['commit_cutoff_ms'];events=d['NN_control_events'];v['requests']+=1
   assert cp['action']==c['action'] and cp['root_visits']==c['root_visits'] and cp['nn_calls']==c['completed_NN'] and cp['generation']==i['generation']
   edges=cp['root_edges'];assert sum(x[2] for x in edges)==cp['root_visits']-1
   # finish is first largest visit in the saved original action order.
   assert max(edges,key=lambda x:x[2])[0]==cp['action']
   assert cp['simulations']==cp['root_visits']-(1 if e=='reference' else 0)
   if e=='candidate':assert cp['terminal_noNN']==c['root_visits']-c['completed_NN']
   out['root_edge_CP_checked']+=1
   status=d['control_final'];assert status['NN_started']==len(events) and status['NN_returned']==len(events)
   v['API_started']+=len(events);v['API_returned']+=len(events);v['discarded']+=sum(x['result_discarded'] for x in events)
   for n in events:
    assert n['engine']==e and n['generation']==i['generation'] and n['request_id']==i['request_id'] and n['start_ms']<=n['session_run_start_ms']<=n['session_run_end_ms']<=n['return_ms']
    v['postpublic_start_definite']+=n['session_run_start_ms']-w['hi_ms']>pub
    v['postcutoff_start_definite']+=n['session_run_start_ms']-w['hi_ms']>cut
    v['postcutoff_start_possible']+=n['session_run_start_ms']-w['lo_ms']>cut
    v['returned_afterpublic_definite']+=n['return_ms']-w['hi_ms']>pub
   ev=next(x for x in d['validation_events'] if x['sequence']==c['sequence'] and x['accepted']);margin=cut-ev['validation_finished_ms'];v['cache_margin_min']=margin if v['cache_margin_min'] is None else min(margin,v['cache_margin_min']);margin=i['deadline_ms']-pub;v['public_margin_min']=margin if v['public_margin_min'] is None else min(margin,v['public_margin_min']);v['ACK_after500']+=r['stop']['main_received_ms']>i['deadline_ms']
   if len(v['clockbrackets'])<8:v['clockbrackets'].append({'id':i['request_id'],'lo':w['lo_ms'],'hi':w['hi_ms'],'error':w['error_ms']})
   assert r['worker_stop_interval_main']['lower_ms']==r['stop']['stop']['at_ms']-w['hi_ms'] and r['worker_stop_interval_main']['upper_ms']==r['stop']['stop']['at_ms']-w['lo_ms']
out['raw_r2_monitor_error_preserved']=json.loads((P/'port151-stageA-r2/pause-monitor-stop.json').read_text())['failure']
out['StageB_group1_control_status_missing_but_saved_monitor_READY']=not (P/'port151-stageB-group1-r1/control-status.json').exists()
for g in range(2,5):
 c=json.loads((P/f'port151-stageB-group{g}-r1/control-status.json').read_text());assert c['state']=='READY' and c['failure'] is None and c['all_owned_read_callbacks_waited']
handoff=pathlib.Path('research-data/ai-sigma/151-sigma-web-port/handoff.json');h=json.loads(handoff.read_text());out['late_handoff']={'SHA256':hashlib.sha256(handoff.read_bytes()).hexdigest(),'data_report_git':h['data_report_git'],'stop_SHA256':h['stop_SHA256'],'StageB_WDL':h['stageB_candidate_WDL'],'same_science_results':hashlib.sha256(pathlib.Path('research-data/ai-sigma/151-sigma-web-port/stageB-results.json').read_bytes()).hexdigest()=='dd7ffd8fc10de57031696b8324cf0eaad3f553d7428beed77e3d7e39f3ccbc3e'}
(D/'clock-detail-result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
