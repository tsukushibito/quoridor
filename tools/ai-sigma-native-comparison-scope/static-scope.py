import datetime,hashlib,json,os,resource
from pathlib import Path
os.sched_setaffinity(0,{0})
root=Path(__file__).resolve().parents[2]
out=root/'research-data/ai-sigma/166-native-comparison-scope'
paths=['.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/mcts_worker.original.js','tools/ai-sigma-actual-boundary-repair/reference-core.js','tools/ai-sigma-native-baseline/reference-core-native.js','tools/ai-sigma-native-baseline/reference.cjs','tools/ai-sigma-native-baseline/common.cjs','tools/ai-sigma-native-baseline/ort.py','research-data/ai-sigma/165-native-baseline/preregister-stageA.json']
records=[]
for name in paths:
 b=(root/name).read_bytes();s=b.decode();records.append({'path':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'setTimeout_tokens':s.count('setTimeout'),'browser_timer_await_tokens':s.count('await new Promise(r=>setTimeout(r,0))')})
assert records[0]['sha256']=='f2de9444e8960ca14d4d4acb5dd319e3f0a6a743c39b4032dce32068ebcfe8fa'
s=(root/paths[2]).read_text();native=s[s.index('async function runMCTS'):s.index('// Pick a child')]
assert 'setTimeout' not in native
ort=(root/paths[5]).read_text()
assert all(t in ort for t in ['intra_op_num_threads=1','inter_op_num_threads=1','ORT_SEQUENTIAL',"providers=['CPUExecutionProvider']",'not controller epoch'])
result={'issue':'quoridor-4lc.166','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'readonly source snapshot and arithmetic; no source execution or model import','sources':records,'native_loop_artificial_timer_absent':True,'native_CPU_provider_settings_present_not_runtime_proven':True,'science_executions':0,'NN':0,'cost_examples_seconds':{'1200_if_public500_and_old_mean_ply':1200*53.5625*.5,'1200_if_public500_old_mean_ply_two_arenas':1200*53.5625*.5/2,'1200_worst200ply_public500':1200*200*.5,'16_worst200ply_public500':16*200*.5},'RAM_self_ru_maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'affinity':sorted(os.sched_getaffinity(0)),'limits':{'RAM_guard':469762048,'new_save_forecast':2097152},'nonclaims':['165 wrapper executed','NN parity','kernel CPU equality','quiescence measured','formal NI','browser NI']}
assert result['RAM_self_ru_maxrss_bytes']<469762048
(out/'static-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'UTC':result['UTC'],'source_count':len(records),'static_supported':True,'NN':0,'RAM':result['RAM_self_ru_maxrss_bytes']}))
