import os,json,subprocess,datetime,time,pathlib
os.sched_setaffinity(0,{0});R=pathlib.Path.cwd();D=R/'research-data/ai-sigma/168-native-stageA-independent';env={**os.environ,'BEADS_ACTOR':'codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'}
logs=[]
def bd(*a):
 t=time.monotonic();p=subprocess.run(['bash','scripts/dev/beads.sh',*a],env=env,capture_output=True,timeout=60);assert p.returncode==0,p.stderr.decode();v=json.loads(p.stdout);logs.append({'command':list(a),'exit':p.returncode,'elapsed':time.monotonic()-t});return v
ready=bd('ready','--json');obs=[]
for id in ['quoridor-4lc','quoridor-4lc.166','quoridor-4lc.168']:
 v=bd('show',id,'--json')[0];obs.append({k:v.get(k) for k in ['id','status','assignee','labels','started_at','updated_at']})
assert obs[0]['status']=='in_progress' and obs[1]['status']=='closed' and obs[2]['assignee']==env['BEADS_ACTOR']
assert all('paused-by-user' not in (x['labels'] or []) for x in obs)
stop=json.loads((R/'research-data/ai-sigma/166-native-comparison-scope/source-stop.json').read_text());assert stop['source_edit_stop'] and not stop['science_child_started']
p=subprocess.run(['bash','scripts/dev/beads.sh','update','quoridor-4lc.168','--claim'],env=env,capture_output=True,timeout=60);assert p.returncode==0,p.stderr.decode();logs.append({'command':['update','quoridor-4lc.168','--claim'],'exit':0})
now=datetime.datetime.now(datetime.timezone.utc);received=datetime.datetime.fromisoformat('2026-10-03T05:04:20+00:00')
old=88190086;prior={}
for n,folders in [('158',['tools/ai-sigma-formal-ni-plan','research-data/ai-sigma/158-formal-ni-plan']),('161',['tools/ai-sigma-formal-clock','research-data/ai-sigma/161-formal-clock']),('166',['tools/ai-sigma-native-comparison-scope','research-data/ai-sigma/166-native-comparison-scope'])]:
 total=0
 for folder in folders:
  for q in (R/folder).rglob('*'):
   if q.is_file():total+=q.stat().st_blocks*512
 prior[n]=total
forecast=8388608;guard=117440512;assert old+sum(prior.values())+forecast<guard
j={'issue':'quoridor-4lc.168','received':received.isoformat(),'claim_and_static_start':now.isoformat(),'contract_Git':'b7d13cccf2b5dae4c820cd71d848425c61cffd0d','newcommand_deadline':(received+datetime.timedelta(minutes=25)).isoformat(),'processing_deadline':(received+datetime.timedelta(minutes=30)).isoformat(),'submission_deadline':(received+datetime.timedelta(minutes=40)).isoformat(),'observed_issues':obs,'166_source_stopped':True,'storage':{'old_conservative':old,'prior_measured_allocated':prior,'new_forecast':forecast,'guard':guard,'total':old+sum(prior.values())+forecast,'unknown_discount':0},'commands':logs,'CPU':[0],'RAM_guard':939524096,'NN':0}
(D/'intake.json').write_text(json.dumps(j,indent=2)+'\n')
(D/'start-report.txt').write_text('goal quoridor-4lc / quoridor-4lc.168 本人受領05:04:20UTC、ready/show goal+self/166 closed・sourcechild停止・pauseなし本人割当確認後claim/静的実開始 '+now.isoformat()+'。契約b7d13ccc。CPU0単1、RAM1GiB guard896、NN0保存算術、180秒総static、新8MiB含むcritic112guard内current+forecast確認。165外heavy ownerへ：CPU0の短static処理予定、StageB gate0、原科学/source編集0。固定10search/320CPと320NN+startup2の対応・最初差・版停止を独自検算し、10分内速報。新NN/Chrome/build/game/取得/委譲0。\n')
print(json.dumps({'claim_and_start':now.isoformat(),'storage':j['storage'],'beads_elapsed':sum(x.get('elapsed',0) for x in logs)}))
