"""Saved-curve/witness arithmetic and lossless checkpoints; no forward."""
import csv
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

D=Path('research-data/ai-sigma/frame15-learning-diagnostic')
sys.path.insert(0,str(Path('tools/nnue-training').resolve()))
from test_contrast import interval

def read_history(path):
    raw=Path(path).read_bytes()
    if str(path).endswith('.gz'):raw=gzip.decompress(raw)
    return [json.loads(s)for s in raw.splitlines()]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

old=read_history('research-data/ai-sigma/frame14-learning/runs/frame14-train96-r1/history.jsonl')
distance=read_history('research-data/ai-sigma/frame14-distance-residual/runs/frame14-distance-residual-r1/history.jsonl')[0]
preregister=json.loads((D/'preregister.json').read_text())
result={'issue':'quoridor-4lc.209','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'condition_count':3,'additional_condition':None,'samples':330630,'extra_observer_NN_samples':0,
        'old_test_labels_results_read':False,'test_evaluated':False,'validation':'reused exploratory; post-selection intervals are descriptive',
        'coefficient_distance_baseline_from_saved_initial_curve':distance['validation']['rootmean_game_equal_mse'],
        'constant_validation':distance['validation']['constant_game_equal_mse'],
        'commonpoint_comparison_tolerance':1e-12,'conditions':{},'initial_SHAs':[],'batch_order_SHAs':[]}
csvrows=[];members=[]
with tarfile.open(D/'weights.tar.xz','w:xz')as archive:
    for run in sorted((D/'runs').iterdir()):
        h=read_history(run/'history.jsonl.gz');o=json.loads((run/'observer.json').read_text());w=read_history(run/'witness.jsonl.gz')
        summary=json.loads((run/'summary.json').read_text());condition=o['condition'];best=next(r for r in h if r['step']==summary['best_step'])
        assert [r['step']for r in h]==preregister['points']
        assert [r['step']for r in w]==preregister['points']
        assert all(r['IDs']==w[0]['IDs']for r in w)
        assert len(w[0]['IDs'])==12
        comparisons={}
        groups={g:v['rootmean_game_equal_mse']for g,v in best['validation_games'].items()}
        initial={g:v['rootmean_game_equal_mse']for g,v in h[0]['validation_games'].items()}
        constant={g:v['constant_game_equal_mse']for g,v in best['validation_games'].items()}
        dist={g:v['rootmean_game_equal_mse']for g,v in distance['validation_games'].items()}
        for name,reference in [('initial',initial),('constant',constant),('distance',dist)]:
            comparisons['best_minus_'+name]=interval(groups,reference,seed=20980311)
        compatibility=[]
        if condition=='lr1e-3':
            for r in h:
                original=next((p for p in old if p['step']==r['step']),None)
                if original:
                    differences={s+'_'+k:abs(r[s][k]-original[s][k])for s in ['train','validation']for k in ['rootmean_mse','rootmean_game_equal_mse','z_mse','z_game_equal_mse']}
                    assert max(differences.values())<=1e-12
                    compatibility.append({'step':r['step'],'maxabs_scalar_metric_diff':max(differences.values())})
        witness_checks=[]
        for v in w:
            changes=[r['prediction']-r['prediction_step0']for r in v['rows']]
            rms=(sum(a*a for a in changes)/len(changes))**.5
            assert abs(rms-v['prediction_step0_RMS_change'])<1e-12
            assert abs(max(abs(a)for a in changes)-v['prediction_step0_maxabs_change'])<1e-12
            assert all(abs(r['prediction']-r['target_rootmean']-r['residual'])<1e-12 for r in v['rows'])
            witness_checks.append({'step':v['step'],'RMS':rms,'maxabs':v['prediction_step0_maxabs_change']})
        for obs in o['observations']:
            for layer in obs['layers'].values():
                assert layer['gradient_all_finite']
                assert layer['gradient_norm']>0
                assert not layer['denominator_zero']
                assert abs(layer['actual_update_norm']/layer['weight_norm_before']-layer['update_to_weight_ratio'])<1e-12
        result['conditions'][condition]={'best_step':summary['best_step'],'best_validation_gameMSE':summary['best_validation_mse'],
            'best_train_gameMSE':best['train']['rootmean_game_equal_mse'],'last_train_gameMSE':h[-1]['train']['rootmean_game_equal_mse'],
            'last_validation_gameMSE':h[-1]['validation']['rootmean_game_equal_mse'],'best_z_gameMSE':best['validation']['z_game_equal_mse'],
            'best_z_sign_row_accuracy':best['validation']['z_sign_accuracy'],'best_saturation_fraction':best['validation']['saturation_fraction'],
            'epoch_best':best['train_epochs_equivalent'],'train_samples_best':best['train_samples_seen'],
            'group_intervals':comparisons,'observer_extra_forward_backward':0,'witness_recalculation':witness_checks,
            'step1_layer':o['observations'][0]['layers'],'step1_ft_active':o['observations'][0]['ft_active_columns'],
            'step400_layer':o['observations'][-1]['layers'],'step400_activation':o['observations'][-1]['activation'],
            'initial_input_scale':w[0]['input_scale'],'initial_witness_SHA':hashlib.sha256(json.dumps(w[0]['IDs']).encode()).hexdigest(),
            'shared_original_commonpoints':compatibility,'run':str(run),'checkpoints':[]}
        for r in h:
            csvrows.append({'condition':condition,'step':r['step'],'samples_seen':r['train_samples_seen'],'epoch':r['train_epochs_equivalent'],
                'all_samples':r['all_samples'],'wall_s':r['elapsed_s'],**{s+'_'+k:r[s][k]for s in ['train','validation']for k in ['rootmean_mse','rootmean_game_equal_mse','z_mse','z_game_equal_mse','z_sign_accuracy','saturation_fraction','constant_game_equal_mse']}})
        weights=Path(summary['checkpoint_dir'])
        for name in ['initial.pt','best.pt','last.pt']:
            p=weights/name;raw=p.read_bytes();member=run.name+'/'+name;info=tarfile.TarInfo(member);info.size=len(raw);info.mtime=0
            archive.addfile(info,io.BytesIO(raw));entry={'member':member,'path':str(p),'SHA':sha(p),'B':len(raw)}
            members.append(entry);result['conditions'][condition]['checkpoints'].append(entry)
        result['initial_SHAs'].append(o['initial_tensor_SHA']);result['batch_order_SHAs'].append(o['batch_order_400_SHA'])
assert len(set(result['initial_SHAs']))==len(set(result['batch_order_SHAs']))==1
with tarfile.open(D/'weights.tar.xz','r:xz')as src:
    for member in members:
        raw=src.extractfile(member['member']).read();assert len(raw)==member['B']and hashlib.sha256(raw).hexdigest()==member['SHA']
(D/'weights-manifest.json').write_text(json.dumps({'archive_SHA':sha(D/'weights.tar.xz'),'B':(D/'weights.tar.xz').stat().st_size,'members':members,'memory_restore_PASS':True,'NN':0},indent=2)+'\n')
with (D/'curves.csv').open('w')as file:
    writer=csv.DictWriter(file,fieldnames=list(csvrows[0]));writer.writeheader();writer.writerows(csvrows)
(D/'diagnostic-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({'conditions':{k:{f:r[f]for f in ['best_step','best_validation_gameMSE','last_train_gameMSE','last_validation_gameMSE','group_intervals']}for k,r in result['conditions'].items()},'samples':result['samples'],'memory_restore':True}))
