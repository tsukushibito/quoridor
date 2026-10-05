"""Saved-result-only summary, curves, stop and exposure access receipt; NN0."""
from pathlib import Path
import datetime,hashlib,json,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning';T=R/'tools/ai-sigma-frame18-data-learning';start=time.monotonic()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
f=json.loads((D/'candidate-freeze-v1.json').read_text());assert all(sha(p)==h for p,h in f['artifacts'].items())
test=json.loads((D/'test-evaluation-r1/result.json').read_text());assert test['freeze_SHA']==sha(D/'candidate-freeze-v1.json')
stages={};histories={}
for n in [192,576]:
 s=json.loads((D/f'learning-plan-v1/settings-{n}.json').read_text());rid=s['run_id'];hist=[json.loads(x)for x in(D/'learning-runs'/rid/'history.jsonl').read_text().splitlines()];histories[n]=hist
 assert [h['step']for h in hist]==[0,1,2,5,10,20,50,100,200,400,800,1200,2000]
 a=json.loads((D/'learning-runs'/rid/'summary.json').read_text());base=json.loads((D/f'learning-plan-v1/baseline-{n}.json').read_text())
 stages[str(n)]={'G':s['positive_train_G'],'all_samples':a['all_samples'],'beststep':a['best_step'],'best_validation_gameMSE':a['best_validation_mse'],'train_epochs_at_2000':hist[-1]['train_epochs_equivalent'],'curve':[{'step':h['step'],'samples':h['train_samples_seen'],'epoch':h['train_epochs_equivalent'],'train':h['train'],'validation':h['validation']}for h in hist],'baseline':base}
secondary={}
for title,sm,lg in [('same_training_samples',2000,2000),('fixed_expected_samples_pergame_nonselection',400,1200)]:
 a=next(h for h in histories[192]if h['step']==sm);b=next(h for h in histories[576]if h['step']==lg);assert set(a['validation_games'])==set(b['validation_games'])
 delta=[b['validation_games'][g]['rootmean_game_equal_mse']-a['validation_games'][g]['rootmean_game_equal_mse']for g in a['validation_games']]
 secondary[title]={'smallstep':sm,'largestep':lg,'small_gameMSE':a['validation']['rootmean_game_equal_mse'],'large_gameMSE':b['validation']['rootmean_game_equal_mse'],'large_minus_small':sum(delta)/len(delta),'gain_games':sum(v<0 for v in delta),'games':len(delta),'noncausal':'samejointseed/reusedvalidation/differentepochs/rowdensity/old96alias'}
process=[]
for p in(D/'learning-guardian').glob('*/process.json'):
 a=json.loads(p.read_text());assert a['exit']==0 and a['reason']is None and a['all_child_waited']and not a['remaining']
 for pid,tick in a['tracked'].items():
  q=Path('/proc')/pid/'stat';assert not q.exists()or int(q.read_text().rsplit(')',1)[1].split()[19])!=tick
 process.append({'path':str(p.resolve()),'SHA':sha(p),**{k:a[k]for k in ['wall_s','samples_actual','peak_family_RSS','tracked','runner_pid','runner_tick']}})
summary={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stages':stages,'stage_comparisons':secondary,'newtest':test,'learning_test_samples':sum(p['samples_actual']for p in process),'learning_test_guardian_wall_s':sum(p['wall_s']for p in process),'peak_family_RSS':max(p['peak_family_RSS']for p in process),'allmodel_science_stopped':True,'no_further_science_in_this_task':True,'newtest_evaluations':1,'goal_achieved':False,'next_max1':'fixed selected scaled QF1 native full/delta/undo parity and bounded alpha-beta connection; a separate allocation, no automatic arena/NI'}
write(D/'learning-test-summary.json',summary)
write(D/'scientific-final-stop.json',{'UTC':summary['UTC'],'learning_test_processes':process,'generation_stop':{'path':str((D/'generation-final-stop-compact.json').resolve()),'SHA':sha(D/'generation-final-stop-compact.json')},'source_SHA':{str(p.resolve()):sha(p)for p in T.glob('*')if p.is_file()},'payload_SHA':{str((D/p).resolve()):sha(D/p)for p in ['candidate-freeze-v1.json','test-evaluation-r1/result.json','test-evaluation-r1/pergame.json','learning-test-summary.json']},'children_waited':True,'current_exact_absent':True,'science_sourcewriter_stopped':True,'remaining_work':'NN0 saved-result plot and necessary payload/Git/notes/backup; immutable scientific inputs','external_host_guarantee':False})
write(D/'protected-artifact-manifest.json',{'prefreeze_allowlist':['dataset-v1/adapter/canonical.jsonl.gz','dataset-v1/adapter/fixed-maximum-mask.json','dataset-v1/training-labels.jsonl.gz','quantity and safe slot ledgers'],'protected_test_refs':['test-sealed/','test-evaluation-r1/'],'labels_access':{'freeze_path':str((D/'candidate-freeze-v1.json').resolve()),'freeze_SHA':sha(D/'candidate-freeze-v1.json'),'access_receipt':str((D/'test-evaluation-r1/access-start.json').resolve()),'one_evaluation_after_freeze':True},'no_OS_allperson_isolation_claim':True,'old_opened_test_labels_read':False})
# Plot from stored metrics only. No Torch import or model forward.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
for n,color in [(192,'#3366cc'),(576,'#dd6633')]:
 h=histories[n];x=[v['train_samples_seen']for v in h]
 for split,style in [('train','--'),('validation','-')]:
  axes[0].plot(x,[v[split]['rootmean_game_equal_mse']for v in h],style,color=color,marker='.',label=f'{n} games {split}')
 axes[0].axhline(stages[str(n)]['baseline']['metrics']['validation']['rootmean_game_equal_mse'],ls=':',color=color,label=f'{n} train-fit distance on val')
names=['candidate','distance','constant','initial']
for target,color in [('rootmean','#3366cc'),('z','#dd6633')]:
 axes[1].plot(names,[test['models'][k]['primary'][target+'_game_equal_mse']for k in names],marker='o',label=target)
axes[0].set(xlabel='Training samples seen',ylabel='Game-equal rootmean MSE',title='Fixed validation96; nested train192/576')
axes[1].set(ylabel='Game-equal MSE',title='One frozen fresh test96 / 4847 eligible rows')
for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=8)
fig.savefig(D/'learning-test-curves.png',dpi=150);fig.savefig(D/'learning-test-curves.svg');plt.close(fig)
write(D/'saved-result-management-cost.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved_result_aggregate_plot_wall_s':time.monotonic()-start,'NN':0,'source_static_and_other_manual_cost':'unmeasured portions retained UNKNOWN; not inferred zero'})
print(json.dumps({'samples':summary['learning_test_samples'],'wall_s':summary['learning_test_guardian_wall_s'],'comparisons':secondary,'management_s':time.monotonic()-start}))
