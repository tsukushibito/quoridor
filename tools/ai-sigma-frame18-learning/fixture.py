"""Finite synthetic NN0 software fixture. No real dataset, labels, or model."""
import argparse
import ast
import copy
import gzip
import json
from pathlib import Path
import sys
import time

import manifest_adapter as a
from loader import load_training_stage
from config_helper import configuration


def run(out):
    start = time.monotonic()
    out.mkdir(parents=True, exist_ok=False)
    cases = []
    def check(name, condition):
        assert condition, name
        cases.append({'case': name, 'result': 'PASS'})
    def reject(name, fn):
        try:
            fn()
        except (ValueError, KeyError) as exc:
            cases.append({'case': name, 'result': 'EXPECTED_REJECTION', 'error': str(exc)})
        else:
            raise AssertionError(name)
    def row(g, split='train', count=0):
        return {'id': g + ':' + str(count), 'game_id': g, 'group': g, 'split': split,
                'side': 1, 'ids': [[0, 81, 290, 301], [1, 82, 291, 302]],
                'distance': [.1, .2], 'state_key': 'state-' + g,
                'history_key': 'state-and-history-' + g}
    for source in Path(__file__).parent.glob('*.py'):
        ast.parse(source.read_text(), filename=str(source))
    check('all private Python sources AST valid', True)
    games = [{'game_id': g, 'family': g, 'split': split, 'cohort': str(8 + 4 * (i % 6)),
              'expected_rows': nr, **({'train_slot': i + 1} if split == 'train' else {})}
             for i, (g, split, nr) in enumerate([('t1', 'train', 2), ('t2', 'train', 1),
                                                ('t3', 'train', 0), ('v1', 'validation', 1),
                                                ('v0', 'validation', 0), ('s1', 'test', 1)])]
    plan = {'kind': 'QF1-dynamic-plan', 'games': games, 'stages': [1, 3]}
    rows = [row('t1'), row('t1', count=1), row('t2'), row('v1', 'validation'), row('s1', 'test')]
    rows[2]['ids'][0][0] = 2
    canonical, mask, stages = a.prepare(plan, rows)
    check('dynamic nested stages 1/3', [s['train_families'] for s in stages] == [1, 3])
    check('planned zero-row/zeroeligible retained', mask['planned_games'] == 6 and
          mask['games']['t3']['rows'] == 0 and 'v0' in mask['zero_eligible_games'])
    check('gameequal not rowequal', stages[-1]['row_sampling_weights']['t1:0'] == .25 and
          stages[-1]['row_sampling_weights']['t2:0'] == .5 and
          abs(sum(stages[-1]['row_sampling_weights'].values()) - 1) < 1e-12)
    check('actual QF1 OR exposure', mask['rows']['v1:0']['exposure'] == ['QF1'])
    same = copy.deepcopy(rows[0]);same['side'] = 2;same['ids'].reverse()
    check('P2 swap same forward input distances already STM',
          a.shared.canonical_model_input(same) == a.shared.canonical_model_input(rows[0]))
    f32same = copy.deepcopy(rows[0]);f32same['distance'][0] += 1e-10
    check('f32 signature ignores JSON f64 difference', a.shared.feature_signature(f32same) == a.shared.feature_signature(rows[0]))
    for key in ('state_key', 'history_key'):
        rs = copy.deepcopy(rows);rs[3]['ids'][0][0] = 7;rs[3][key] = rs[0][key]
        check(key + ' independently excludes', key.replace('_key', '') in a.prepare(plan, rs)[1]['rows']['v1:0']['exposure'])
    bad = copy.deepcopy(plan);bad['games'][3]['family'] = 't1'
    reject('sibling family cannot cross partition', lambda: a.prepare(bad, rows))
    bad = copy.deepcopy(plan);bad['games'][1]['train_slot'] = 1
    reject('slot assignment inconsistency', lambda: a.prepare(bad, rows))
    bad = copy.deepcopy(plan);bad['games'][1]['game_id'] = 't1'
    reject('duplicate planned game', lambda: a.prepare(bad, rows))
    reject('duplicate row', lambda: a.prepare(plan, rows + [rows[0]]))
    reject('missing owner-advertised row', lambda: a.prepare(plan, rows[1:]))
    for field, value in [('side', True), ('distance', [False, .2]), ('ids', [[0, 0, 1, 2], [0, 1, 2, 3]]), ('rootmean', .5)]:
        rs = copy.deepcopy(rows);rs[0][field] = value
        reject('row schema ' + field, lambda rs=rs: a.prepare(plan, rs))
    alias = copy.deepcopy(plan);alias['games'][0]['source_split'] = 'evaluation'
    rs = copy.deepcopy(rows);rs[0]['split'] = rs[1]['split'] = 'evaluation'
    check('explicit new-manifest train alias preserves source',
          a.prepare(alias, rs)[0][1]['source_split'] == 'evaluation')
    reject('implicit old partition reassignment', lambda: a.prepare(plan, rs))
    bad = copy.deepcopy(plan);bad['stages'] = [1, 2]
    reject('largest train frozen once not partial', lambda: a.prepare(bad, rows))
    labels = [{'id': r['id'], 'split': r['split'], 'rootmean': .1, 'z': 1} for r in rows if r['split'] != 'test']
    label_path = out / 'SYNTHETIC-train-validation-labels.json'
    label_path.write_text(json.dumps(labels))
    bound = copy.deepcopy(plan);bound['training_labels_advertised'] = {'path': str(label_path.resolve()), 'sha256': a.shared.sha(label_path)}
    # Observe that preparation only opens source code and outputs, never labels.
    original_read = Path.read_bytes
    def guarded_read(p):
        if p.resolve() == label_path.resolve():
            raise AssertionError('preparation opened labels')
        return original_read(p)
    Path.read_bytes = guarded_read
    try:
        a.write_bundle(bound, rows, out / 'dynamic', {'fixture': 'synthetic-only'})
    finally:
        Path.read_bytes = original_read
    check('prepare advertisements only, no label read', True)
    one, m1 = load_training_stage(out / 'dynamic/1.stage.json')
    maximum, m3 = load_training_stage(out / 'dynamic/3.stage.json')
    check('future shared loader synthetic-only stage join', len(one) == 3 and len(maximum) == 4 and not any(r['split'] == 'test' for r in maximum))
    check('same fixed validation mask for both stages', m1['mask_sha256'] == m3['mask_sha256'] and
          [r['primary_eligible'] for r in one if r['split'] == 'validation'] ==
          [r['primary_eligible'] for r in maximum if r['split'] == 'validation'])
    check('all zero eligible validation denominators retained', m3['planned_partition_games']['validation'] == 2 and
          m3['zero_eligible_validation_families'] == ['v0', 'v1'])
    # Bind a synthetic missing/test-label artifact separately; immutable success bundle stays intact.
    for name, badlabels in [('missing', labels[1:]), ('test', labels + [{'id': 's1:0', 'split': 'test', 'rootmean': 0}])]:
        path = out / (name + '-SYNTHETIC-labels.json');path.write_text(json.dumps(badlabels))
        b = copy.deepcopy(m3);b['training_labels'] = str(path.resolve());b['training_labels_sha256'] = a.shared.sha(path)
        manifest = out / (name + '.stage.json');manifest.write_text(json.dumps(b))
        reject('loader ' + name + ' label denial', lambda manifest=manifest: load_training_stage(manifest))
    reject('immutable prepared success output', lambda: a.write_bundle(bound, rows, out / 'dynamic', {}))
    legacygames, legacyrows = [], []
    for i in range(96):
        g = 'legacy-' + str(i + 1)
        legacygames.append({'game_id': g, 'family': g, 'split': 'train', 'cohort': '8', 'expected_rows': 1, 'train_slot': i + 1})
        legacyrows.append(row(g))
    legacy = {'kind': 'QF1-dynamic-plan', 'games': legacygames, 'stages': [24, 48, 96]}
    check('legacy max96/stages24/48/96 semantics',
          [s['train_rows'] for s in a.prepare(legacy, legacyrows)[2]] == [24, 48, 96])
    cfg, settings = configuration(100, 20, '/advertised/scale.json', '0' * 64)
    check('shared config accepts private proposal', cfg['training']['sampling'] == 'game' and cfg['optimizer']['lr'] == .0001)
    check('no val/test statistics fit; scale only advertised', settings['statistics_partitions'] == ['train'] and settings['model_training_connected'] is False)
    check('no model/Torch/Numpy imported', not any(n == 'torch' or n.startswith('torch.') or n == 'numpy' for n in sys.modules))
    result = {'kind': 'synthetic-NN0-software-fixture', 'cases': cases, 'case_count': len(cases),
              'wall_seconds': time.monotonic() - start, 'real_rows': 0, 'real_labels_opened': 0,
              'NN': 0, 'model_imports': 0, 'train': 0, 'test_evaluation': 0,
              'limitations': ['not a real dataset qualification', 'no model forward or training',
                              'scale/dense evaluation remain future thin integration']}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--out', required=True)
    run(Path(parser.parse_args().out))
