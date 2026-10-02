from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT';U=R/'.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA';out=[];hashes={}
for base in [U/'initial-pair1-r1',O/'critic95-golden-r1',O/'critic95-four-ply-r1']:
 p=base/('real-'+base.name+'-session1')/'private-after-public.json';b=p.read_bytes();hashes[str(p)]=hashlib.sha256(b).hexdigest();priv=json.loads(b);turns=[json.loads(x) for x in (base/'turns.jsonl').read_text().splitlines()];rows=[]
 for t in turns:
  q=priv[t['request_id']];NN=q['NN'];end=NN[-1]['session_run_end_ms'] if NN else None;stop=t['owned_zero']['at_ms'];r={'id':t['request_id'],'engine':t['engine'],'ACK_cause_ms':t['cause_window_ms'],'public_ms':t['public_elapsed_ms'],'Worker_lastAPI_to_stop_exact_same_clock_ms':None if end is None else stop-end,'Worker_private_done_to_stop_same_clock_ms':stop-q['worker_done_ms'],'NN_attempts':t['owned_zero']['NN_attempts'],'NN_completed':len(NN),'cp_completion_sim':t['root_cp']['simulations'],'public_completed_sim':next(json.loads(x)['response']['completed_simulations'] for x in (base/'public.jsonl').read_text().splitlines() if json.loads(x)['identity']['request_id']==t['request_id'])};assert r['Worker_private_done_to_stop_same_clock_ms']>=0;rows.append(r)
 per={}
 for e in ['candidate','reference']:
  a=[x for x in rows if x['engine']==e];per[e]={'worst_ACK':max(a,key=lambda x:x['ACK_cause_ms']),'max_lastAPI_to_stop_exact':max(x['Worker_lastAPI_to_stop_exact_same_clock_ms'] for x in a)}
 out.append({'run':base.name,'per_engine':per,'rows':rows})
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items());(O/'cause-components.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':out,'input_hashes':hashes,'scope':'same Worker clock cancels offset for lastAPI-to-stop; no attribution to pure IPC/OS or kernel CPU'},indent=2)+'\n');print(json.dumps([{'run':x['run'],'per_engine':x['per_engine']} for x in out]))
