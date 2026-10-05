"""Explicit mask/stage/freeze/test commands; no automatic training or selection."""
import argparse
import gzip
import json
import random
import time
import traceback
from pathlib import Path

from common import measurements, write_json
from frame14_data import bound_path, digest, feature_signature, load_stage, make_mask, read_rows, sha


def new_json(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def mask(args):
    rows = read_rows(args.metadata)
    m = make_mask(rows)
    m['metadata_sha256'] = sha(args.metadata)
    if args.openings:
        plan=json.loads(Path(args.openings).read_text())['games']
        expected={'train':96,'validation':24,'test':24}
        if {s:sum(g['split']==s for g in plan) for s in expected} != expected:
            raise ValueError('planned144 partition counts changed')
        families={}
        for g in plan:
            if g['family'] in families:
                raise ValueError('frame14 plan requires 144 distinct families')
            families[g['family']]=g['split']
            if g['family'] not in m['games']:
                m['games'][g['family']]={'split':g['split'],'rows':0,'eligible':0}
        if any(families.get(r['group'])!=r['split'] for r in rows):
            raise ValueError('row partition differs from planned family')
        m['planned_train_groups']=[g['family'] for g in sorted([g for g in plan if g['split']=='train'],key=lambda g:g['partition_slot'])]
        m['planned_openings_sha256']=sha(args.openings)
        m['zero_eligible_games']=sorted(g for g,v in m['games'].items() if not v['eligible'])
    new_json(args.output, m)
    print(json.dumps({'rows': len(rows), 'games': len(m['games']), 'zero_eligible_games': m['zero_eligible_games']}))


def canonicalize(args):
    rows=read_rows(args.metadata)
    make_mask(rows)  # Refuses labels and malformed identity/exposure input.
    for r in rows:
        r['QF1_input_sha256']=feature_signature(r)
    with Path(args.output).open('xb') as f:
        f.write(gzip.compress(('\n'.join(json.dumps(r,separators=(',',':')) for r in rows)+'\n').encode(),mtime=0))
    print(json.dumps({'rows':len(rows),'sha256':sha(args.output),'labels_read':False}))


def stage(args):
    rows = read_rows(args.metadata)
    m = json.loads(Path(args.mask).read_text())
    if m['metadata_sha256'] != sha(args.metadata):
        raise ValueError('mask metadata binding')
    groups = {}
    for r in rows:
        if r['split'] == 'train':
            if not isinstance(r.get('train_slot'), int):
                raise ValueError('result-before train_slot required')
            if r['group'] in groups and groups[r['group']] != r['train_slot']:
                raise ValueError('family spans nested training slots')
            groups[r['group']] = r['train_slot']
    ordered = m.get('planned_train_groups', sorted(groups, key=lambda g: (groups[g], g)))
    if len(ordered) != 96:
        raise ValueError('max-train96 exposure universe not complete')
    spec = {'kind': 'QF1-training-stage', 'train_games': args.games,
            'train_groups': ordered[:args.games], 'test_labels_allowed': False}
    for key in ['metadata', 'mask', 'training_labels']:
        p = getattr(args, key)
        spec[key] = str(Path(p).resolve())
        spec[key+'_sha256'] = sha(p)
    # Validate access/partition/IDs without Torch or test labels.
    new_json(args.output, spec)
    load_stage(args.output)
    print(json.dumps({'stage': args.output, 'games': args.games}))


def freeze(args):
    run = Path(args.run)
    cfg = json.loads((run/'config.json').read_text())
    info = json.loads((run/'dataset.json').read_text())
    summary = json.loads((run/'summary.json').read_text())
    if summary['status'] != 'max_steps' or summary['step'] != cfg['training']['steps']:
        raise ValueError('candidate incomplete; no silent partial adoption')
    w = Path(summary['checkpoint_dir'])
    cp, initial = w/'best.pt', w/'initial.pt'
    if cfg['training']['target'] != 'rootmean' or cfg['evaluation']['monitor'] != 'game':
        raise ValueError('frame14 primary metric fixed')
    stage_spec = info['stage_manifest']
    if not stage_spec:
        raise ValueError('candidate needs stage/mask provenance')
    for key in ('metadata','mask','training_labels'):
        bound_path(stage_spec, key)
    frozen = {'kind': 'QF1-one-candidate-test-freeze', 'checkpoint': str(cp.resolve()),
              'checkpoint_sha256': sha(cp), 'initial_checkpoint': str(initial.resolve()),
              'initial_checkpoint_sha256': sha(initial), 'config': cfg, 'config_sha256': digest(cfg),
              'dataset_sha256': info['sha256'], 'validation_sha256': info['validation_sha256'],
              'stage_manifest': stage_spec, 'constant': info['constant'],
              'constant_source': 'candidate train-only gameequal target mean',
              'initial_state_sha256': info['initial_state_sha256'], 'best_step': summary['best_step'],
              'validation_primary_metric': summary['best_validation_mse'],
              'selection_reason': args.reason, 'run': str(run.resolve()),
              'test_labels': str(Path(args.test_labels).resolve()), 'test_labels_sha256': args.test_sha,
              'test_labels_opened': False, 'test_rule': 'primary mask / secondary all, paired group-bootstrap2000 seed19580311',
              'source_sha256': {n: sha(Path(__file__).with_name(n)) for n in ['frame14.py','frame14_data.py','common.py','model.py']}}
    if len(args.test_sha) != 64:
        raise ValueError('test sealed SHA required before open')
    new_json(args.output, frozen)
    print(json.dumps({'freeze': args.output, 'sha256': sha(args.output), 'test_opened': False}))


def bootstrap(rows, predictions):
    grouped = {}
    for r, v in zip(rows, predictions):
        if r.get('rootmean') is not None:
            grouped.setdefault(r['group'], []).append((v-r['rootmean'])**2)
    return {g: sum(v)/len(v) for g, v in grouped.items()}


def paired_intervals(groups_by_model):
    keys = sorted(set.intersection(*(set(x) for x in groups_by_model.values())))
    result = {'groups': len(keys), 'replicates': 2000, 'seed': 19580311,
              'small_sample_limit': 'game/family correlations and 24 planned games; exploratory percentile interval'}
    if len(keys) < 2:
        result['intervals'] = None
        return result
    rng = random.Random(19580311)
    draws = [[rng.choice(keys) for _ in keys] for _ in range(2000)]
    result['candidate_minus_baseline'] = {}
    for name in ['initial', 'constant']:
        d = sorted(sum(groups_by_model['candidate'][g]-groups_by_model[name][g] for g in sample)/len(sample) for sample in draws)
        result['candidate_minus_baseline'][name] = {'mean': sum(groups_by_model['candidate'][g]-groups_by_model[name][g] for g in keys)/len(keys), 'percentile95': [d[49], d[1949]]}
    return result


def evaluate(args):
    start = time.monotonic()
    if sha(args.freeze) != args.freeze_sha:
        raise ValueError('freeze artifact differs from admitted SHA')
    f = json.loads(Path(args.freeze).read_text())
    out = Path(args.output)
    # One-shot claim is durable before labels open; exceptions keep this directory.
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'started.json', {'freeze_sha256': sha(args.freeze), 'monotonic': start, 'test_reselection_allowed': False})
    count = 0
    try:
        if f['kind'] != 'QF1-one-candidate-test-freeze' or digest(f['config']) != f['config_sha256']:
            raise ValueError('freeze kind/config')
        for n, h in f['source_sha256'].items():
            if sha(Path(__file__).with_name(n)) != h:
                raise ValueError('evaluation source changed after freeze: '+n)
        cp, init = bound_path(f, 'checkpoint'), bound_path(f, 'initial_checkpoint')
        m = f['stage_manifest']
        meta = read_rows(bound_path(m, 'metadata'))
        masks = json.loads(bound_path(m, 'mask').read_text())
        if masks['metadata_sha256'] != sha(m['metadata']):
            raise ValueError('test mask metadata mismatch')
        test = [r for r in meta if r['split'] == 'test']
        if 2*len(test)>args.samples:
            raise ValueError('test sample cap before labels')
        labels = read_rows(bound_path(f, 'test_labels'))
        if any(r.get('split') != 'test' for r in labels):
            raise ValueError('sealed label partition')
        by_id = {r['id']: r for r in labels}
        if len(by_id) != len(labels) or set(by_id) != {r['id'] for r in test}:
            raise ValueError('test label IDs inconsistent')
        rows = [{**r, 'rootmean': by_id[r['id']].get('rootmean'), 'z': by_id[r['id']].get('z')} for r in test]
        for r in rows:
            if masks['rows'][r['id']]['split']!='test' or masks['rows'][r['id']]['group']!=r['group']:
                raise ValueError('test mask identity')
            for target in ('rootmean','z'):
                v=r[target]
                if v is not None and (not isinstance(v,(int,float)) or not -1<=v<=1):
                    raise ValueError('invalid test target')
        import torch
        from model import Model, inputs
        torch.set_num_threads(1); torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        predictions = {}
        for name, p in [('candidate', cp), ('initial', init)]:
            loaded = torch.load(p, map_location='cpu', weights_only=True)
            if loaded['model_config'] != f['config']['model'] or loaded['dataset_sha256']!=f['dataset_sha256']:
                raise ValueError('checkpoint model/dataset mismatch')
            model = Model(f['config']['model']); model.load_state_dict(loaded['model']); model.eval()
            values = []
            with torch.inference_mode():
                for begin in range(0,len(rows),1024):
                    if time.monotonic()-start>args.seconds:
                        raise ValueError('test wall limit')
                    b=rows[begin:begin+1024]; count+=len(b)
                    values.extend(model(*inputs(b)).tolist())
            predictions[name] = values
        predictions['constant'] = [f['constant']]*len(rows)
        primary_ix = [i for i,r in enumerate(rows) if masks['rows'][r['id']]['primary_eligible']]
        result={'freeze_sha256':sha(args.freeze), 'test_labels_sha256':f['test_labels_sha256'],
                'samples':count,'warm':0,'elapsed_s':time.monotonic()-start,'planned_test_games':24,
                'actual_test_games':len({r['group'] for r in rows}), 'all_rows':len(rows),'primary_rows':len(primary_ix),
                'zero_eligible_games':sorted(g for g,v in masks['games'].items() if v['split']=='test' and not v['eligible']),
                'test_reselection_allowed':False,'strength_claim':False,'models':{}}
        groups = {}
        for name, values in predictions.items():
            result['models'][name]={'primary':measurements([rows[i] for i in primary_ix],[values[i] for i in primary_ix],'rootmean',f['constant']),
                                    'secondary_all':measurements(rows,values,'rootmean',f['constant']),'games':{},'cohorts':{},'phase':{}}
            groups[name]=bootstrap([rows[i] for i in primary_ix],[values[i] for i in primary_ix])
            for g in sorted({r['group'] for r in rows}):
                ix=[i for i,r in enumerate(rows) if r['group']==g]; px=[i for i in ix if i in primary_ix]
                result['models'][name]['games'][g]={'primary':measurements([rows[i] for i in px],[values[i] for i in px],'rootmean',f['constant']),
                                                   'secondary_all':measurements([rows[i] for i in ix],[values[i] for i in ix],'rootmean',f['constant'])}
            for c in sorted({r.get('cohort','all') for r in rows}):
                ix=[i for i in primary_ix if rows[i].get('cohort','all')==c]
                result['models'][name]['cohorts'][c]=measurements([rows[i] for i in ix],[values[i] for i in ix],'rootmean',f['constant'])
            for phase in ['early','middle','late']:
                ix=[i for i in primary_ix if ('early' if rows[i].get('ply',0)<40 else 'middle' if rows[i].get('ply',0)<100 else 'late')==phase]
                result['models'][name]['phase'][phase]=measurements([rows[i] for i in ix],[values[i] for i in ix],'rootmean',f['constant'])
        result['bootstrap']=paired_intervals(groups)
        raw=[{'id':r['id'],'game':r['group'],'rootmean':r['rootmean'],'z':r['z'],
              'mask':masks['rows'][r['id']], 'candidate':predictions['candidate'][i], 'initial':predictions['initial'][i]} for i,r in enumerate(rows)]
        (out/'per-row.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(r,separators=(',',':'),allow_nan=False) for r in raw)+'\n').encode(),mtime=0))
        write_json(out/'result.json',result)
        print(json.dumps({k:v for k,v in result.items() if k!='models'}))
    except BaseException as exc:
        write_json(out/'failure.json', {'typed':'TEST_NUMERIC_OR_SCHEMA_OR_BUDGET_UNSETTLED','error':repr(exc),'samples':count,'traceback':traceback.format_exc()})
        raise


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('mask'); a.add_argument('--metadata',required=True);a.add_argument('--openings');a.add_argument('--output',required=True);a.set_defaults(fn=mask)
    a=sub.add_parser('canonicalize');a.add_argument('--metadata',required=True);a.add_argument('--output',required=True);a.set_defaults(fn=canonicalize)
    a=sub.add_parser('stage')
    for key in ['metadata','mask','training-labels','output']:a.add_argument('--'+key,required=True)
    a.add_argument('--games',type=int,choices=[24,48,96],required=True);a.set_defaults(fn=stage)
    a=sub.add_parser('freeze')
    for key in ['run','test-labels','test-sha','output','reason']:a.add_argument('--'+key,required=True)
    a.set_defaults(fn=freeze)
    a=sub.add_parser('evaluate');a.add_argument('--freeze',required=True);a.add_argument('--freeze-sha',required=True);a.add_argument('--output',required=True)
    a.add_argument('--seconds',type=float,default=100);a.add_argument('--samples',type=int,required=True);a.set_defaults(fn=evaluate)
    args=p.parse_args();args.fn(args)
