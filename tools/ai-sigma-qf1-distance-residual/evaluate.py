"""One new sealed test evaluation; private residual and analytical baselines."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

sys.path.insert(0, str(Path('tools/nnue-training').resolve()))
from common import measurements, write_json
from frame14_data import read_rows, sha
from test_contrast import interval, group_losses, group_sign

D = Path('research-data/ai-sigma/frame14-distance-residual')


def evaluate(a):
    start = time.monotonic()
    count = 0
    f = json.loads(Path(a.freeze).read_text())
    assert sha(a.freeze) == a.freeze_sha
    out = D / 'test-evaluation-r1'
    out.mkdir(exist_ok=False)
    write_json(out / 'started.json', {'freeze_SHA': a.freeze_sha, 'reselection': False})
    try:
        for p, h in f['sources'].items():
            assert sha(p) == h, p
        for artifact in f['artifacts'].values():
            assert sha(artifact['path']) == artifact['checkpoint_SHA']
        meta = read_rows(f['metadata']['path'])
        assert sha(f['metadata']['path']) == f['metadata']['SHA']
        assert sha(f['mask']['path']) == f['mask']['SHA']
        mask = json.loads(Path(f['mask']['path']).read_text())
        rows = [r for r in meta if r['split'] == 'test']
        assert len({r['id'] for r in rows}) == len(rows)
        unique = {(r['condition'], r['weight_SHA']) for r in f['artifacts'].values()}
        assert len(unique) <= 4 and len(unique) * len(rows) <= a.samples <= 12000
        assert mask['metadata_sha256'] == f['metadata']['SHA']
        planned = sorted(g for g, m in mask['games'].items() if m['split'] == 'test')
        assert len(planned) == 24 and set(r['group'] for r in rows) <= set(planned)
        assert f['coefficient_fit_SHA'] == '77ce9e79495038b25a4f4a9ffd95dc9f66700aff2c1f96cf08b65fff3c79733c'
        # Exclusive marker precedes the first fresh test label read; no old test access.
        with (D / 'test-open-once.json').open('x') as file:
            json.dump({'freeze_SHA': a.freeze_sha, 'test_labels_SHA': f['labels']['SHA'],
                       'old_test_read': False, 'reselection': False}, file, indent=2)
        assert sha(f['labels']['path']) == f['labels']['SHA']
        labels = read_rows(f['labels']['path'])
        assert all(r['split'] == 'test' for r in labels)
        by_id = {r['id']: r for r in labels}
        assert len(by_id) == len(labels) and set(by_id) == {r['id'] for r in rows}
        rows = [{**r, 'rootmean': by_id[r['id']].get('rootmean'), 'z': by_id[r['id']].get('z')} for r in rows]
        for r in rows:
            mr = mask['rows'][r['id']]
            assert mr['split'] == 'test' and mr['group'] == r['group']
            assert all(v is None or (isinstance(v, (int, float)) and math.isfinite(v) and -1 <= v <= 1)
                       for v in [r['rootmean'], r['z']])
        import torch
        from model import Model, inputs
        from residual_model import ResidualModel, A, B
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        x = inputs(rows)
        predictions, reused, by_weight = {}, {}, {}
        for name, artifact in f['artifacts'].items():
            cp = torch.load(artifact['path'], map_location='cpu', weights_only=True)
            h = hashlib.sha256(b''.join(v.numpy().tobytes() for v in cp['model'].values())).hexdigest()
            assert h == artifact['weight_SHA'] and cp['model_config'] == f['model_config']
            assert cp['target'] == 'rootmean'
            key = (artifact['condition'], h)
            if key in by_weight:
                predictions[name] = by_weight[key][1]
                reused[name] = by_weight[key][0]
                continue
            model = ResidualModel(cp['model_config']) if artifact['condition'] == f['condition'] else Model(cp['model_config'])
            model.load_state_dict(cp['model'], strict=True)
            if isinstance(model, ResidualModel):
                model._initial = False
                assert model.distance_a.item() == torch.tensor(A, dtype=torch.float32).item()
                assert model.distance_b.item() == torch.tensor(B, dtype=torch.float32).item()
            model.eval()
            values = []
            with torch.inference_mode():
                for begin in range(0, len(rows), 1024):
                    end = min(begin + 1024, len(rows))
                    assert time.monotonic() - start < 110 and count + end - begin <= a.samples
                    v = model(*(q[begin:end] for q in x))
                    count += end - begin
                    assert bool(torch.isfinite(v).all())
                    values.extend(v.tolist())
            by_weight[key] = (name, values)
            predictions[name] = values
        # Analytical distance/constant incur no NN model forward.
        d = x[1]
        predictions['distance_only'] = (torch.tensor(A, dtype=torch.float32) +
                                       torch.tensor(B, dtype=torch.float32) * (d[:, 1] - d[:, 0])).clamp(-1, 1).tolist()
        predictions['constant'] = [f['constant']] * len(rows)
        initial_diff = max((abs(a-b) for a, b in zip(predictions['distance_initial'], predictions['distance_only'])), default=0.)
        assert initial_diff == 0
        ix = [i for i, r in enumerate(rows) if mask['rows'][r['id']]['primary_eligible']]
        selected = [rows[i] for i in ix]
        zero = [g for g in planned if not any(rows[i]['group'] == g for i in ix)]
        result = {'freeze_SHA': a.freeze_sha, 'samples': count, 'unique_NN_models': len(by_weight),
                  'prediction_reused': reused, 'warm': 0, 'GPU': 0, 'elapsed_s': time.monotonic() - start,
                  'planned_test_games': 24, 'actual_test_games': len({r['group'] for r in rows}),
                  'eligible_test_games': len({r['group'] for r in selected}), 'zero_eligible_games': zero,
                  'all_rows': len(rows), 'primary_rows': len(ix), 'excluded_rows': len(rows)-len(ix),
                  'mask_summary': mask.get('summary'), 'distance_initial_maxabs': initial_diff,
                  'models': {}, 'paired_intervals': {}, 'strength_claim': False, 'test_reselection_allowed': False,
                  'teacher_rootmean_is_not_truth': True, 'old_test_labels_read': False}
        selected_values = {}
        for name, values in predictions.items():
            pv = [values[i] for i in ix]
            selected_values[name] = pv
            m = {'primary': measurements(selected, pv, 'rootmean', f['constant']),
                 'secondary_all': measurements(rows, values, 'rootmean', f['constant']),
                 'games': {}, 'phase': {}, 'cohorts': {}}
            for g in planned:
                gi = [i for i, r in enumerate(rows) if r['group'] == g]
                pi = [i for i in gi if i in ix]
                m['games'][g] = {'primary': measurements([rows[i] for i in pi], [values[i] for i in pi], 'rootmean', f['constant']),
                                 'secondary_all': measurements([rows[i] for i in gi], [values[i] for i in gi], 'rootmean', f['constant'])}
            for phase in ['early', 'middle', 'late']:
                pi = [i for i in ix if ('early' if rows[i].get('ply', 0)<40 else 'middle' if rows[i].get('ply', 0)<100 else 'late') == phase]
                m['phase'][phase] = measurements([rows[i] for i in pi], [values[i] for i in pi], 'rootmean', f['constant'])
            for cohort in sorted({r.get('cohort', 'all') for r in rows}):
                pi = [i for i in ix if rows[i].get('cohort', 'all') == cohort]
                m['cohorts'][cohort] = measurements([rows[i] for i in pi], [values[i] for i in pi], 'rootmean', f['constant'])
            result['models'][name] = m
        for target in ['rootmean', 'z', 'z_sign']:
            gs = {n: group_sign(selected, v) if target == 'z_sign' else group_losses(selected, v, target)
                  for n, v in selected_values.items()}
            result['paired_intervals'][target] = {}
            for name, reference in f['paired_comparisons']:
                result['paired_intervals'][target][name+'_minus_'+reference] = interval(gs[name], gs[reference], seed=20080311)
        raw = [{'id': r['id'], 'game': r['group'], 'rootmean': r['rootmean'], 'z': r['z'],
                'mask': mask['rows'][r['id']], 'values': {n: v[i] for n, v in predictions.items()}}
               for i, r in enumerate(rows)]
        (out / 'per-row.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(r, separators=(',', ':'), allow_nan=False)
                                                                          for r in raw)+'\n').encode(), mtime=0))
        result['elapsed_s'] = time.monotonic() - start
        write_json(out / 'result.json', result)
        print(json.dumps({k: v for k, v in result.items() if k not in ['models', 'paired_intervals']}))
    except BaseException as exc:
        write_json(out / 'failure.json', {'typed': 'TEST_NUMERIC_OR_SCHEMA_OR_BUDGET_UNSETTLED',
                                         'error': repr(exc), 'samples': count, 'traceback': traceback.format_exc()})
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--freeze', required=True)
    p.add_argument('--freeze-sha', required=True)
    p.add_argument('--samples', type=int, required=True)
    evaluate(p.parse_args())
