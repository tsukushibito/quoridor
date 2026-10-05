"""Private, label-free dynamic stage preparation. No model or training imports.

Plan games specify game_id, family, split, cohort, expected_rows, and train_slot
for train families. Optional source_split permits an explicit new-manifest alias;
the source dataset and original row IDs are never rewritten. Stages count families.
Training-label advertisements are paths/hashes only: prepare never opens them.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/nnue-training'))
import frame14_data as shared

VERSION = 'frame18-dynamic-stage-v1'
LABEL_KEYS = {'rootmean', 'z', 'z_stm', 'loss', 'rootNN', 'winner', 'target',
              'prediction', 'value', 'pi', 'policy'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer(v):
    return type(v) is int


def row_schema(r):
    require(not LABEL_KEYS.intersection(r), 'labels prohibited in preparation')
    for k in ('id', 'game_id', 'group', 'state_key', 'history_key'):
        require(isinstance(r.get(k), str) and bool(r[k]), 'missing identity: ' + k)
    require(integer(r.get('side')) and r['side'] in (1, 2), 'invalid STM view')
    ids = r.get('ids')
    require(isinstance(ids, list) and len(ids) == 2, 'two fixed views required')
    for view in ids:
        require(isinstance(view, list) and 4 <= len(view) <= 24 and
                all(integer(x) and 0 <= x < 312 for x in view) and
                len(view) == len(set(view)), 'invalid sparse feature IDs')
    d = r.get('distance')
    require(isinstance(d, list) and len(d) == 2 and
            all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                for x in d), 'invalid STM float32 distances')
    shared.canonical_model_input(r)  # Distances already STM ordered: no second swap.


def prepare(plan, rows):
    require(plan.get('kind') == 'QF1-dynamic-plan', 'plan kind')
    games = plan.get('games', [])
    require(bool(games), 'empty game plan')
    by_game, families = {}, {}
    for g in games:
        for key in ('game_id', 'family', 'cohort'):
            require(isinstance(g.get(key), str) and bool(g[key]), 'game plan ' + key)
        require(g['game_id'] not in by_game, 'duplicate planned game ID')
        require(g.get('split') in ('train', 'validation', 'test'), 'planned split')
        require(integer(g.get('expected_rows')) and g['expected_rows'] >= 0,
                'owner-advertised row count required')
        if g['split'] == 'train':
            require(integer(g.get('train_slot')) and g['train_slot'] > 0, 'train slot')
        identity = (g['split'], g.get('train_slot'), g['cohort'])
        require(g['family'] not in families or families[g['family']] == identity,
                'sibling family assignment/cohort inconsistency')
        families[g['family']] = identity
        by_game[g['game_id']] = g
    train = sorted((slot, f) for f, (split, slot, _) in families.items() if split == 'train')
    require([slot for slot, _ in train] == list(range(1, len(train) + 1)),
            'train family slots must be unique and contiguous')
    stages = plan.get('stages')
    require(isinstance(stages, list) and bool(stages) and
            all(integer(n) and 0 < n <= len(train) for n in stages) and
            stages == sorted(set(stages)) and stages[-1] == len(train),
            'nested stages must end at the frozen maximum train')
    seen, counts, canonical = set(), Counter(), []
    for original in rows:
        row_schema(original)
        require(original['id'] not in seen, 'duplicate row ID')
        seen.add(original['id'])
        require(original['game_id'] in by_game, 'row outside planned games')
        g = by_game[original['game_id']]
        require(original['group'] == g['family'], 'row family mismatch')
        require(original.get('split') == g.get('source_split', g['split']),
                'source split mismatch; reassignment must be explicit')
        r = dict(original, split=g['split'], cohort=g['cohort'])
        if r['split'] != original['split']:
            r['source_split'] = original['split']
        if r['split'] == 'train':
            r['train_slot'] = g['train_slot']
        canonical.append(r)
        counts[g['game_id']] += 1
    for g in games:
        require(counts[g['game_id']] == g['expected_rows'],
                'missing/excess rows: ' + g['game_id'])
    canonical.sort(key=lambda r: (r['split'], r['group'], r['game_id'], r['id']))
    mask = shared.make_mask(canonical)
    mask.update(adapter_version=VERSION, plan_sha256=shared.digest(plan),
                largest_train_families=len(train), labels_used=False,
                rule='state OR history OR actual STM-f32 QF1 input; fixed maximum train',
                feature_version='QF1-f32-STM-v1')
    for f, (split, _, _) in families.items():
        mask['games'].setdefault(f, {'split': split, 'rows': 0, 'eligible': 0})
    mask['zero_eligible_games'] = sorted(f for f, g in mask['games'].items() if not g['eligible'])
    mask['planned_games'] = len(games)
    mask['planned_families'] = len(families)
    mask['planned_partition_games'] = dict(Counter(g['split'] for g in games))
    mask['planned_partition_families'] = dict(Counter(v[0] for v in families.values()))
    descriptors = []
    for n in stages:
        chosen = [f for _, f in train[:n]]
        selected = [r for r in canonical if r['split'] == 'train' and r['group'] in chosen]
        per_group = Counter(r['group'] for r in selected)
        positive = len(per_group)
        # This is the original family/game-equal sampling distribution for all
        # available training rows. Future target masks require their own report.
        weights = {r['id']: 1 / (positive * per_group[r['group']]) for r in selected}
        descriptors.append({'train_families': n, 'train_groups': chosen,
                            'train_games': sum(g['split'] == 'train' and g['family'] in chosen for g in games),
                            'train_rows': len(selected), 'positive_train_families': positive,
                            'zero_row_train_families': sorted(set(chosen) - set(per_group)),
                            'cohort_families': dict(Counter(families[f][2] for f in chosen)),
                            'row_sampling_weights': weights,
                            'sampling': 'uniform positive family then uniform row; target eligibility not inspected'})
    return canonical, mask, descriptors


def advertised_labels(plan):
    ad = plan.get('training_labels_advertised')
    if ad is None:
        return None
    require(set(ad) == {'path', 'sha256'} and isinstance(ad['path'], str) and
            isinstance(ad['sha256'], str) and len(ad['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in ad['sha256']), 'label advertisement')
    return ad


def write_bundle(plan, rows, out, inputs):
    canonical, mask, descriptors = prepare(plan, rows)
    ad = advertised_labels(plan)
    require(not out.exists(), 'immutable output already exists')
    out.mkdir(parents=True)
    def write(name, obj):
        (out / name).write_text(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n')
    meta = out / 'canonical.jsonl.gz'
    meta.write_bytes(gzip.compress(b''.join((json.dumps(r, sort_keys=True, allow_nan=False) + '\n').encode() for r in canonical), mtime=0))
    write('fixed-maximum-mask.json', mask)
    metadata_sha, mask_sha = shared.sha(meta), shared.sha(out / 'fixed-maximum-mask.json')
    for stage in descriptors:
        n = stage['train_families']
        write(str(n) + '-sampling.json', stage)
        m = {'kind': 'QF1-training-stage' if ad else 'QF1-stage-preparation',
             'adapter_version': VERSION, 'train_groups': stage['train_groups'],
             'train_games': stage['train_games'], 'train_family_count': n,
             'metadata': str(meta.resolve()), 'metadata_sha256': metadata_sha,
             'mask': str((out / 'fixed-maximum-mask.json').resolve()), 'mask_sha256': mask_sha,
             'plan_sha256': shared.digest(plan), 'largest_train_family_count': descriptors[-1]['train_families'],
             'labels_opened': False, 'training_ready': False,
             'future_required': 'authorized label hash/schema/target-mask verification and bound load_stage'}
        if ad:
            m.update(training_labels=ad['path'], training_labels_sha256=ad['sha256'])
        write(str(n) + '.stage.json', m)
    write('preparation-receipt.json', {'adapter_version': VERSION, 'plan_sha256': shared.digest(plan),
          'source_sha256': shared.sha(__file__), 'shared_source_sha256': shared.sha(shared.__file__),
          'input_bindings': inputs, 'metadata_sha256': metadata_sha, 'mask_sha256': mask_sha,
          'planned_games': len(plan['games']), 'rows': len(canonical),
          'labels_opened': False, 'model_imports': False, 'training_ready': False,
          'statistics': 'none; no validation/test data fit or train statistics',
          'future_test_sealed_advertisement': plan.get('sealed_test_advertised')})
    return metadata_sha, mask_sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True)
    p.add_argument('--metadata', action='append', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    rows, inputs = [], {}
    for path in a.metadata:
        inputs[str(Path(path).resolve())] = shared.sha(path)
        rows.extend(shared.read_rows(path))
    print(json.dumps({'metadata_sha256_and_mask_sha256': write_bundle(plan, rows, Path(a.out), inputs),
                      'labels_opened': False, 'NN': 0}))


if __name__ == '__main__':
    main()
