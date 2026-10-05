"""Exactly two CPU forwards over preregistered validation only; no training."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, time, traceback

D = Path('research-data/ai-sigma/186-value-game-diagnostic')


def save(name, x):
    (D / name).write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')


def main():
    start = time.monotonic()
    pr = json.loads((D / 'preregister.json').read_text())
    assert os.sched_getaffinity(0) == {8}
    assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(pr['newNN_before_UTC'].replace('Z', '+00:00'))
    source = Path(pr['dataset'])
    assert hashlib.sha256(source.read_bytes()).hexdigest() == pr['dataset_SHA256']
    rows = []
    with gzip.open(source, 'rt') as f:
        for line in f:
            row = json.loads(line)
            if row['split'] == 'validation':
                rows.append(row)
    rows.sort(key=lambda r: (r['lineage'], r['game_id'], r['row_id']))
    ids = [{k: r[k] for k in ['row_id', 'game_id', 'lineage', 'side', 'ply']} for r in rows]
    raw = json.dumps(ids, separators=(',', ':'), sort_keys=True).encode()
    assert hashlib.sha256(raw).hexdigest() == pr['ID_order_SHA256']
    assert len(rows) == 502 and len({r['row_id'] for r in rows}) == 502
    assert all(r['lineage'].startswith(('native176-', 'native181-')) for r in rows)
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    class PV(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.hidden = torch.nn.Linear(648, 32)
            self.policy = torch.nn.Linear(32, 136)
            self.value = torch.nn.Linear(32, 1)

        def forward(self, x):
            h = torch.relu(self.hidden(x.flatten(1)))
            return self.policy(h), torch.tanh(self.value(h))

    x = torch.from_numpy(np.asarray([r['features648_bits'] for r in rows], dtype=np.uint32).view(np.float32).copy()).reshape(-1, 8, 9, 9)
    pi = torch.tensor([r['pi136'] for r in rows], dtype=torch.float32)
    z = torch.tensor([r['z_stm'] if r['value_eligible'] else 0 for r in rows], dtype=torch.float32)
    vm = torch.tensor([float(r['value_eligible']) for r in rows])
    mask = torch.zeros((len(rows), 136), dtype=torch.bool)
    for i, row in enumerate(rows):
        for _, k in row['mapping136']:
            mask[i, k] = True
    assert torch.isfinite(x).all() and torch.isfinite(pi).all()
    assert torch.all(pi[~mask] == 0) and torch.allclose(pi.sum(1), torch.ones(len(rows)), atol=1e-6, rtol=0)
    assert torch.all(vm == 1) and torch.all((z >= -1) & (z <= 1))
    output, counters = {}, dict(forward_calls=0, samples=0, warm=0, GPU=0, train=0)
    for name in ['old', 'new']:
        path, expected = pr['models'][name]
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
        state = torch.load(path, map_location='cpu', weights_only=True)
        assert all(v.device.type == 'cpu' and v.dtype == torch.float32 for v in state.values())
        model = PV().cpu()
        model.load_state_dict(state, strict=True)
        model.eval()
        assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(pr['newNN_before_UTC'].replace('Z', '+00:00'))
        counters['forward_calls'] += 1
        counters['samples'] += len(rows)
        assert counters['samples'] <= 1200
        save('counters.json', counters)  # Charge before call, including failed calls.
        with torch.inference_mode():
            logits, value = model(x)
            assert logits.shape == (502, 136) and value.shape == (502, 1)
            assert torch.isfinite(logits).all() and torch.isfinite(value).all()
            value = value[:, 0]
            assert torch.all((value >= -1) & (value <= 1))
            ce = -(pi * torch.log_softmax(logits.masked_fill(~mask, -1e9), dim=1)).sum(1)
            mse = (value - z) ** 2 * vm
        assert torch.isfinite(ce).all() and torch.isfinite(mse).all()
        output[name] = dict(value=value.tolist(), ce=ce.tolist(), mse=mse.tolist())
        del model, state, logits, value, ce, mse
    assert counters == dict(forward_calls=2, samples=1004, warm=0, GPU=0, train=0)
    recs = []
    for i, row in enumerate(rows):
        r = {k: row[k] for k in ['row_id', 'game_id', 'lineage', 'side', 'ply', 'z_stm', 'value_eligible']}
        r['cohort'] = 'old' if row['lineage'].startswith('native176-') else 'new'
        for name in ['old', 'new']:
            for metric in ['value', 'ce', 'mse']:
                r[name + '_' + metric] = output[name][metric][i]
        r['delta_mse'] = r['new_mse'] - r['old_mse']
        r['delta_ce'] = r['new_ce'] - r['old_ce']
        recs.append(r)
    with gzip.GzipFile(filename=str(D / 'per-row.jsonl.gz'), mode='wb', mtime=0) as f:
        for r in recs:
            f.write((json.dumps(r, separators=(',', ':')) + '\n').encode())

    def summary(rs):
        result = dict(rows=len(rs), groups=len({r['lineage'] for r in rs}), targets={str(t): sum(r['z_stm'] == t for r in rs) for t in [-1, 0, 1]})
        for name in ['old', 'new']:
            ce = sum(r[name + '_ce'] for r in rs) / len(rs)
            mse = sum(r[name + '_mse'] for r in rs) / len(rs)
            result[name] = dict(CE=ce, MSE=mse, total=ce + mse,
                               mean_value=sum(r[name + '_value'] for r in rs) / len(rs),
                               mean_target=sum(r['z_stm'] for r in rs) / len(rs),
                               sign_correct=sum(r[name + '_value'] * r['z_stm'] > 0 for r in rs),
                               saturated=sum(abs(r[name + '_value']) >= .9 for r in rs),
                               calibration_by_target={str(t): dict(n=sum(r['z_stm'] == t for r in rs), mean_pred=sum(r[name + '_value'] for r in rs if r['z_stm'] == t) / sum(r['z_stm'] == t for r in rs)) for t in [-1, 0, 1] if any(r['z_stm'] == t for r in rs)})
        result['delta_MSE'] = result['new']['MSE'] - result['old']['MSE']
        result['delta_CE'] = result['new']['CE'] - result['old']['CE']
        result['rows_MSE_worse'] = sum(r['delta_mse'] > 0 for r in rs)
        return result

    cohort = {name: summary([r for r in recs if r['cohort'] == name]) for name in ['old', 'new']}
    groups = []
    for game in sorted({r['game_id'] for r in recs}):
        rs = [r for r in recs if r['game_id'] == game]
        item = summary(rs)
        item.update(game_id=game, lineage=rs[0]['lineage'], cohort=rs[0]['cohort'],
                    delta_MSE_sum=sum(r['delta_mse'] for r in rs),
                    contribution_to_cohort_delta=sum(r['delta_mse'] for r in rs) / cohort[rs[0]['cohort']]['rows'])
        groups.append(item)
    receipt = json.loads(Path(pr['receipt']).read_text())
    comparisons = []
    for model, key in [('old', 'loss_before'), ('new', 'loss_after')]:
        for c, ck in [('old', 'original_validation'), ('new', 'new_validation')]:
            expected = receipt[key][ck]
            actual = [cohort[c][model][m] for m in ['total', 'CE', 'MSE']]
            for metric, a, e in zip(['total', 'CE', 'MSE'], actual, expected):
                tol = pr['aggregate_tolerance']['abs'] + pr['aggregate_tolerance']['rtol'] * abs(e)
                comparisons.append(dict(model=model, cohort=c, metric=metric, actual=a, receipt=e, difference=a-e, tolerance=tol, accepted=abs(a-e) <= tol))
    settled = all(r['accepted'] for r in comparisons)
    result = dict(status='PASS' if settled else 'NUMERIC_OR_SCHEMA_UNSETTLED', cohorts=cohort, overall=summary(recs), groups=groups,
                  receipt_comparisons=comparisons, counters=counters, torch=str(torch.__version__),
                  threads=[torch.get_num_threads(), torch.get_num_interop_threads()],
                  wall_seconds=time.monotonic()-start, game_correlation=True, independent_rows=False,
                  view='z/value root side-to-move; pi legal action mapping unchanged; rootmean_aux0',
                  next_cause_unique=False, strength_claim=False)
    save('results.json', result)
    print(json.dumps(dict(status=result['status'], counters=counters, wall_seconds=result['wall_seconds'])))


if __name__ == '__main__':
    try:
        main()
    except BaseException as e:
        save('failure.json', dict(status='NUMERIC_OR_SCHEMA_UNSETTLED', error=repr(e), traceback=traceback.format_exc()))
        raise
