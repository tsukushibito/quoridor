from pathlib import Path
import datetime,hashlib,json
D=Path('research-data/ai-sigma/frame18-data-learning');T=Path('tools/ai-sigma-frame18-data-learning')
read=lambda p:json.loads(p.read_text());g=read(D/'generation-final-stop-compact.json');s=read(D/'learning-test-summary.json');q=read(D/'background-generation-progress.json');pack=read(D/'learning-payload-receipt.json')
scope=sum(p.stat().st_size for r in[D,T]for p in r.rglob('*')if p.is_file())
known_firstpack=sum(read(D/'jobs'/n/'pack-receipt.json')['pack_Git_restore_cleanup_wall_s']for n in ['val96-chunk1-r1','val96-chunk2-r1'])
m=q['management_measured_s']+known_firstpack
cost={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new672GOAL':672,'Rjoint':32520,'density_joint_per_newgame':32520/672,'generation_allattempt_physicalNN':g['physicalNN_allattempt'],'generation_NNcap':2200000,'generation_guardian_wall_s':g['guardian_allattempt_wall_s'],'generation_wallcap_s':5400,'learning_test_samples':s['learning_test_samples'],'learning_test_samplecap':2000000,'learning_test_wall_s':s['learning_test_guardian_wall_s'],'learning_test_wallcap_s':900,'generation_management_measured_lowerbound_s':m,'pack_measured_s':pack['management_wall_s'],'plot_management_failure_charge_conservative_s':30,'source_manual_freeze_reporting_Git_backup_cost':'some portions unmeasured UNKNOWN; not zero and not double-added to overlapping background wall','genqueue_idle_s':q['idle_wait_s'],'root_hold_s':657.929311,'root_test_CPU_s':6.550977,'1000_job_allattempt_extrapolation_min':g['guardian_allattempt_wall_s']*1000/672/60,'1000_generation_known_with_measured_management_lowerbound_min':(g['guardian_allattempt_wall_s']+m)*1000/672/60,'1000_caveat':'short-workload extrapolation + other unmeasured pipeline/scale/tail costs; 1000 NOT_RUN; 30min unmet','actual_scope_B':scope,'unique_Git_forecast_B':128*1024**2,'temp_residual_forecast_B':32*1024**2,'accounted_scope_forecast_B':scope+160*1024**2,'guard_B':448*1024**2,'reservation_B':512*1024**2,'experiment_pool_MiB':1980,'last_confirmed_pool_unused_after_229_B':157392896,'no_reservation_release_claim':True,'old_unknown_discount_B':0,'parent_added_B':0}
assert cost['accounted_scope_forecast_B']<cost['guard_B']
assert cost['generation_allattempt_physicalNN']<cost['generation_NNcap']and cost['learning_test_samples']<2000000
cost['default_index_SHA']=hashlib.sha256(Path('/workspaces/quoridor/.git/worktrees/ai-sigma/index').read_bytes()).hexdigest()
assert cost['default_index_SHA']=='59880a1d93833b8a0ea250e9a2b1270c41ceb9f6666da9ab0edeb48991817072'
(D/'final-storage-caps-cost.json').write_text(json.dumps(cost,indent=2)+'\n')
print(json.dumps(cost))
