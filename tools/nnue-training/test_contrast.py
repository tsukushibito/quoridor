"""One sealed test opening: selected candidate and predeclared last-last contrast."""
import argparse
import gzip
import json
from pathlib import Path
import random
import time
import traceback

from common import measurements, write_json
from frame14_data import bound_path, digest, read_rows, sha
from frame14 import new_json


def bind_run(path):
    run=Path(path);summary=json.loads((run/'summary.json').read_text())
    config=json.loads((run/'config.json').read_text());data=json.loads((run/'dataset.json').read_text())
    if (summary['status']!='max_steps' or summary['step']!=2000 or config['training']['steps']!=2000 or config['training']['batch_size']!=128
        or summary['last_evaluation']['train_samples_seen']!=256000):
        raise ValueError('quantity contrast requires complete2000step/256000samples')
    p=Path(summary['checkpoint_dir'])/'last.pt'
    return {'checkpoint':str(p.resolve()),'checkpoint_sha256':sha(p),'config':config,'dataset':data,
            'step':2000,'train_samples':256000,'initial_state_sha256':data['initial_state_sha256'],
            'run':str(run.resolve())}


def quantity_freeze(a):
    f=json.loads(Path(a.candidate_freeze).read_text())
    if f['kind']!='QF1-one-candidate-test-freeze':raise ValueError('candidate freeze kind')
    x,y=bind_run(a.stage24),bind_run(a.stage96)
    if x['initial_state_sha256']!=y['initial_state_sha256'] or x['initial_state_sha256']!=f['initial_state_sha256']:
        raise ValueError('initial weights differ')
    for key in ['model','optimizer','training','evaluation']:
        if x['config'][key]!=y['config'][key]:raise ValueError('quantity config differs: '+key)
    if x['config']['optimizer']['lr']!=.001 or x['config']['training']['seed']!=19080311 or x['config']['training']['target']!='rootmean':
        raise ValueError('quantity original fixed condition')
    for r,n in [(x,24),(y,96)]:
        m=r['dataset']['stage_manifest']
        if m['train_games']!=n or m['mask_sha256']!=f['stage_manifest']['mask_sha256'] or r['dataset']['validation_sha256']!=f['validation_sha256']:
            raise ValueError('quantity dataset/fixed-mask validation binding')
    f.update({'kind':'QF1-one-test-with-fixed-quantity-contrast','candidate_freeze_sha256':sha(a.candidate_freeze),
              'quantity':{'stage24_last':x,'stage96_last':y},
              'quantity_rule':'paired96minus24 LAST at256000 training samples each; no pure quantity/epoch causal claim',
              'test_rule':'one opening; candidate/initial/24last/96last at most4 unique SHA + train-only constant; paired group bootstrap2000',
              'quantity_declared_before_test':True})
    f['source_sha256']['test_contrast.py']=sha(Path(__file__))
    new_json(a.output,f);print(json.dumps({'freeze':a.output,'sha256':sha(a.output),'test_opened':False}))


def interval(a,b,seed=19580311):
    keys=sorted(set(a)&set(b))
    if len(keys)<2:return {'groups':len(keys),'delta':None,'percentile95':None}
    rng=random.Random(seed)
    values=[]
    for _ in range(2000):
        sample=[rng.choice(keys) for _ in keys]
        values.append(sum(a[g]-b[g] for g in sample)/len(sample))
    values.sort()
    return {'groups':len(keys),'delta':sum(a[g]-b[g] for g in keys)/len(keys),'percentile95':[values[49],values[1949]],'seed':seed,'replicates':2000}


def group_losses(rows,values,target):
    g={}
    for r,v in zip(rows,values):
        if r.get(target) is not None:g.setdefault(r['group'],[]).append((v-r[target])**2)
    return {k:sum(v)/len(v) for k,v in g.items()}


def group_sign(rows,values):
    g={}
    for r,v in zip(rows,values):
        if r.get('z') not in (None,0):g.setdefault(r['group'],[]).append(v*r['z']>0)
    return {k:sum(v)/len(v) for k,v in g.items()}


def evaluate(a):
    start=time.monotonic()
    if sha(a.freeze)!=a.freeze_sha:raise ValueError('admitted freeze SHA changed')
    f=json.loads(Path(a.freeze).read_text());out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    write_json(out/'started.json',{'freeze_sha256':a.freeze_sha,'test_reselection_allowed':False,'one_opening':True})
    count=0
    try:
        if f['kind']!='QF1-one-test-with-fixed-quantity-contrast' or digest(f['config'])!=f['config_sha256']:
            raise ValueError('freeze kind/config')
        for name,h in f['source_sha256'].items():
            if sha(Path(__file__).with_name(name))!=h:raise ValueError('frozen source changed: '+name)
        artifacts={'candidate':{'checkpoint':f['checkpoint'],'checkpoint_sha256':f['checkpoint_sha256'],'config':f['config'],'dataset_sha256':f['dataset_sha256']},
                   'initial':{'checkpoint':f['initial_checkpoint'],'checkpoint_sha256':f['initial_checkpoint_sha256'],'config':f['config'],'dataset_sha256':f['dataset_sha256']}}
        for name,r in f['quantity'].items():artifacts[name]={'checkpoint':r['checkpoint'],'checkpoint_sha256':r['checkpoint_sha256'],'config':r['config'],'dataset_sha256':r['dataset']['sha256']}
        for r in artifacts.values():bound_path(r,'checkpoint')
        m=f['stage_manifest'];meta=read_rows(bound_path(m,'metadata'));mask=json.loads(bound_path(m,'mask').read_text())
        if mask['metadata_sha256']!=sha(m['metadata']):raise ValueError('mask metadata binding')
        test=[r for r in meta if r['split']=='test']
        unique=len({r['checkpoint_sha256'] for r in artifacts.values()})
        if unique*len(test)>a.samples:raise ValueError('test upper sample cap before opening')
        # One frame14 test opening across output names and candidate configurations.
        new_json(Path('research-data/ai-sigma/frame14-learning/test-open-once.json'),
                 {'freeze_sha256':a.freeze_sha,'test_labels_sha256':f['test_labels_sha256'],'output':str(out.resolve()),'reselection_allowed':False})
        labels=read_rows(bound_path(f,'test_labels')) # Only test opening, after all freeze checks.
        if any(r.get('split')!='test' for r in labels):raise ValueError('sealed partition')
        by_id={r['id']:r for r in labels}
        if len(by_id)!=len(labels) or set(by_id)!={r['id'] for r in test}:raise ValueError('sealed IDs')
        rows=[{**r,'rootmean':by_id[r['id']].get('rootmean'),'z':by_id[r['id']].get('z')} for r in test]
        for r in rows:
            if mask['rows'][r['id']]['split']!='test' or mask['rows'][r['id']]['group']!=r['group']:raise ValueError('mask ID binding')
            if any(v is not None and (not isinstance(v,(int,float)) or not -1<=v<=1) for v in [r['rootmean'],r['z']]):raise ValueError('nonfinite test labels')
        import torch
        from model import Model,inputs
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        x=inputs(rows);predictions={};by_sha={}
        for name,r in artifacts.items():
            h=r['checkpoint_sha256']
            if h in by_sha:predictions[name]=by_sha[h];continue
            cp=torch.load(r['checkpoint'],map_location='cpu',weights_only=True)
            if cp['model_config']!=r['config']['model'] or cp['dataset_sha256']!=r['dataset_sha256']:raise ValueError('checkpoint provenance')
            model=Model(r['config']['model']);model.load_state_dict(cp['model']);model.eval();values=[]
            with torch.inference_mode():
                for begin in range(0,len(rows),1024):
                    if time.monotonic()-start>=a.seconds:raise ValueError('test wall limit')
                    end=min(begin+1024,len(rows));count+=end-begin
                    values.extend(model(*(v[begin:end] for v in x)).tolist())
            by_sha[h]=values;predictions[name]=values
        predictions['constant']=[f['constant']]*len(rows)
        ix=[i for i,r in enumerate(rows) if mask['rows'][r['id']]['primary_eligible']]
        selected=[rows[i] for i in ix]
        result={'freeze_sha256':a.freeze_sha,'samples':count,'unique_NN_models':unique,'warm':0,'GPU':0,'elapsed_s':time.monotonic()-start,
                'planned_test_games':24,'all_rows':len(rows),'primary_rows':len(ix),'actual_test_games':len({r['group'] for r in rows}),
                'zero_eligible_games':sorted(g for g,v in mask['games'].items() if v['split']=='test' and not v['eligible']),
                'models':{},'teacher_rootmean_is_not_truth':True,'strength_claim':False,'test_reselection_allowed':False}
        selected_values={}
        for name,values in predictions.items():
            pv=[values[i] for i in ix];selected_values[name]=pv
            result['models'][name]={'primary':measurements(selected,pv,'rootmean',f['constant']),
                                    'secondary_all':measurements(rows,values,'rootmean',f['constant']),'games':{},'cohorts':{}}
            for group in sorted(g for g,v in mask['games'].items() if v['split']=='test'):
                gi=[i for i,r in enumerate(rows) if r['group']==group];pi=[i for i in gi if i in ix]
                result['models'][name]['games'][group]={'primary':measurements([rows[i] for i in pi],[values[i] for i in pi],'rootmean',f['constant']),
                                                        'secondary_all':measurements([rows[i] for i in gi],[values[i] for i in gi],'rootmean',f['constant'])}
            for cohort in sorted({r.get('cohort','all') for r in rows}):
                ci=[i for i in ix if rows[i].get('cohort','all')==cohort]
                result['models'][name]['cohorts'][cohort]=measurements([rows[i] for i in ci],[values[i] for i in ci],'rootmean',f['constant'])
        result['paired_intervals']={}
        for target in ['rootmean','z']:
            g={name:group_losses(selected,v,target) for name,v in selected_values.items()}
            result['paired_intervals'][target]={'candidate_minus_initial':interval(g['candidate'],g['initial']),
                                               'candidate_minus_constant':interval(g['candidate'],g['constant']),
                                               'quantity96_minus24':interval(g['stage96_last'],g['stage24_last'])}
        g={name:group_sign(selected,v) for name,v in selected_values.items()}
        result['paired_intervals']['z_sign_quantity96_minus24']=interval(g['stage96_last'],g['stage24_last'])
        raw=[{'id':r['id'],'game':r['group'],'rootmean':r['rootmean'],'z':r['z'],'mask':mask['rows'][r['id']],
              'values':{k:v[i] for k,v in predictions.items() if k!='constant'}} for i,r in enumerate(rows)]
        (out/'per-row.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(r,separators=(',',':'),allow_nan=False) for r in raw)+'\n').encode(),mtime=0))
        write_json(out/'result.json',result);print(json.dumps({k:v for k,v in result.items() if k!='models'}))
    except BaseException as exc:
        write_json(out/'failure.json',{'typed':'TEST_NUMERIC_OR_SCHEMA_OR_BUDGET_UNSETTLED','error':repr(exc),'samples':count,'traceback':traceback.format_exc()});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('freeze')
    for key in ['candidate-freeze','stage24','stage96','output']:a.add_argument('--'+key,required=True)
    a.set_defaults(fn=quantity_freeze)
    a=s.add_parser('evaluate')
    for key in ['freeze','freeze-sha','output']:a.add_argument('--'+key,required=True)
    a.add_argument('--samples',type=int,required=True);a.add_argument('--seconds',type=float,default=110);a.set_defaults(fn=evaluate)
    a=p.parse_args();a.fn(a)
