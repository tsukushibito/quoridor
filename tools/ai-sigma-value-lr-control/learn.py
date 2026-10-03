"""One LR-only CPU training control; 200 fixed steps plus two validation batches."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, time, traceback

D = Path('research-data/ai-sigma/188-value-lr-control')


def save(name, x):
    (D / name).write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')


def main():
    start = time.monotonic()
    pr = json.loads((D / 'preregister.json').read_text())
    assert os.sched_getaffinity(0) == {8}
    assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(pr['newscience_before_UTC'].replace('Z', '+00:00'))
    source = Path(pr['dataset'])
    assert hashlib.sha256(source.read_bytes()).hexdigest() == pr['dataset_SHA256']
    allrows = []
    rows = []
    with gzip.open(source, 'rt') as f:
        for line in f:
            row = json.loads(line)
            allrows.append(row)
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
    torch.random.default_generator.manual_seed(18180311)

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
    output, counters = {}, dict(forward_calls=0, samples=0, warm=0, train_steps=0, GPU=0)
    path, expected = pr['models']['old']
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    state = torch.load(path, map_location='cpu', weights_only=True)
    assert all(v.device.type == 'cpu' and v.dtype == torch.float32 for v in state.values())
    model = PV().cpu()  # Same seeded construction as181 before loading parent.
    model.load_state_dict(state, strict=True)
    model.eval()
    trainrows = [r for r in allrows if r['split'] == 'train']  # Original file order.
    assert len(trainrows) == 2260
    tx = torch.from_numpy(np.asarray([r['features648_bits'] for r in trainrows], dtype=np.uint32).view(np.float32).copy()).reshape(-1,8,9,9)
    tpi = torch.tensor([r['pi136'] for r in trainrows], dtype=torch.float32)
    tz = torch.tensor([[r['z_stm'] if r['value_eligible'] else 0] for r in trainrows], dtype=torch.float32)
    tvm = torch.tensor([[float(r['value_eligible'])] for r in trainrows])
    tmask = torch.zeros((2260,136),dtype=torch.bool)
    for i,r in enumerate(trainrows):
        for _,k in r['mapping136']:tmask[i,k]=True
    assert torch.isfinite(tx).all() and torch.all(tpi[~tmask]==0)
    ledger=[]; minibatch_sha=hashlib.sha256()
    def charge(n,training=False):
        counters['forward_calls']+=1;counters['samples']+=n
        if training:counters['train_steps']+=1
        assert counters['samples']<=26604
        save('counters.json',counters)
    for name in ['old','new']:
        if name == 'new':
            model.train()
            for step in range(200):
                idx=torch.randint(len(trainrows),(128,))
                minibatch_sha.update(idx.numpy().tobytes())
                model.zero_grad(set_to_none=True);charge(128,True)
                logits,value=model(tx[idx])
                ce=-(tpi[idx]*torch.log_softmax(logits.masked_fill(~tmask[idx],-1e9),dim=1)).sum(1).mean()
                mse=(((value-tz[idx])**2)*tvm[idx]).sum()/tvm[idx].sum().clamp_min(1)
                total=ce+mse;assert torch.isfinite(total);total.backward()
                assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
                if step in [0,19,49,99,199]:ledger.append(dict(step=step+1,total=float(total.detach()),CE=float(ce.detach()),MSE=float(mse.detach())))
                with torch.no_grad():
                    for p in model.parameters():p.add_(p.grad,alpha=-.0025)
                assert all(torch.isfinite(p).all()for p in model.parameters())
            model.eval()
        charge(502)
        with torch.inference_mode():
            logits, value = model(x)
            assert logits.shape == (502,136) and value.shape == (502,1)
            assert torch.isfinite(logits).all() and torch.isfinite(value).all()
            value=value[:,0]
            ce=-(pi*torch.log_softmax(logits.masked_fill(~mask,-1e9),dim=1)).sum(1)
            mse=(value-z)**2*vm
        output[name]=dict(value=value.tolist(),ce=ce.tolist(),mse=mse.tolist())
        if name=='old':
            b=[json.loads(v)for v in gzip.decompress(Path(pr['baseline_per_row']).read_bytes()).splitlines()]
            assert [r['row_id']for r in b]==[r['row_id']for r in rows]
            assert all(abs(output['old'][m][i]-r['old_'+m])<=1e-6+1e-6*abs(r['old_'+m])for i,r in enumerate(b)for m in ['value','ce','mse']),'BEFORE_NUMERIC_OR_SCHEMA_UNSETTLED'
    assert counters==dict(forward_calls=202,samples=26604,warm=0,train_steps=200,GPU=0)
    checkpoint=D/'student-checkpoint.pt';assert not checkpoint.exists(),'NO_SUCCESS_REPLACEMENT'
    torch.save(model.state_dict(),checkpoint)
    reloaded=torch.load(checkpoint,map_location='cpu',weights_only=True)
    assert all(torch.equal(v,reloaded[k])for k,v in model.state_dict().items())
    save('training.json',dict(LR=.0025,seed=18180311,steps=200,minibatch=128,ledger=ledger,minibatch_sequence_SHA256=minibatch_sha.hexdigest(),checkpoint_SHA256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),checkpoint_bytes=checkpoint.stat().st_size,weights_only_reload_bit_equal=True,reload_forward=0,sample_counter=counters))
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
    for model, key in [('old', 'loss_before')]:
        for c, ck in [('old', 'original_validation'), ('new', 'new_validation')]:
            expected = receipt[key][ck]
            actual = [cohort[c][model][m] for m in ['total', 'CE', 'MSE']]
            for metric, a, e in zip(['total', 'CE', 'MSE'], actual, expected):
                tol = pr['aggregate_tolerance']['abs'] + pr['aggregate_tolerance']['rtol'] * abs(e)
                comparisons.append(dict(model=model, cohort=c, metric=metric, actual=a, receipt=e, difference=a-e, tolerance=tol, accepted=abs(a-e) <= tol))
    prior = [json.loads(v) for v in gzip.decompress(Path(pr['baseline_per_row']).read_bytes()).splitlines()]
    assert hashlib.sha256(Path(pr['baseline_per_row']).read_bytes()).hexdigest()==pr['baseline_per_row_SHA256']
    assert [r['row_id'] for r in prior]==[r['row_id'] for r in recs]
    per_row_diff=[]
    for r,b in zip(recs,prior):
        for m in ['value','ce','mse']:
            tol=1e-6+1e-6*abs(b['old_'+m]);per_row_diff.append(abs(r['old_'+m]-b['old_'+m])/tol)
    comparisons.append(dict(metric='before_vs186_all_row_scalars',max_diff_over_tol=max(per_row_diff),accepted=max(per_row_diff)<=1))
    save('baseline-181-reference.json',dict(source=pr['baseline_per_row'],SHA256=pr['baseline_per_row_SHA256'],control_LR=.01,new_checkpoint=pr['models']['new'][1],no_new_control_forward=True))
    settled = all(r['accepted'] for r in comparisons)
    result = dict(status='PASS' if settled else 'NUMERIC_OR_SCHEMA_UNSETTLED', cohorts=cohort, overall=summary(recs), groups=groups,
                  receipt_comparisons=comparisons, counters=counters, torch=str(torch.__version__),
                  threads=[torch.get_num_threads(), torch.get_num_interop_threads()],
                  wall_seconds=time.monotonic()-start, game_correlation=True, independent_rows=False,
                  view='old=parent176 before; new=LR.0025 after; z/value root side-to-move; pi legal; rootmean_aux0',
                  next_cause_unique=False, strength_claim=False)
    save('results.json', result)
    print(json.dumps(dict(status=result['status'], counters=counters, wall_seconds=result['wall_seconds'])))


if __name__ == '__main__':
    try:
        main()
    except BaseException as e:
        save('failure.json', dict(status='NUMERIC_OR_SCHEMA_UNSETTLED', error=repr(e), traceback=traceback.format_exc()))
        raise
