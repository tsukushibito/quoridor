"""Label-free exposure masks and manifest-bound training/test access."""
import gzip
import hashlib
import json
import struct
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read_rows(path):
    raw = Path(path).read_bytes()
    if str(path).endswith('.gz'):
        raw = gzip.decompress(raw)
    if str(path).removesuffix('.gz').endswith('.jsonl'):
        return [json.loads(x) for x in raw.splitlines() if x.strip()]
    j = json.loads(raw)
    return j['samples'] if isinstance(j, dict) else j


def bound_path(manifest, key):
    p = Path(manifest[key]).resolve()
    if sha(p) != manifest[key + '_sha256']:
        raise ValueError('manifest binding changed: ' + key)
    return p


def canonical_model_input(r):
    """Single shared input contract: STM views and exact float32 distance bits."""
    p = r['side'] - 1
    if p not in (0, 1) or len(r['distance']) != 2:
        raise ValueError('invalid canonical model input')
    bits = [struct.unpack('<I', struct.pack('<f', v))[0] for v in r['distance']]
    return ['QF1-f32-STM-v1', sorted(r['ids'][p]), sorted(r['ids'][1-p]), bits]


def feature_signature(r):
    return digest(canonical_model_input(r))


def signatures(r):
    if not r.get('state_key') or not r.get('history_key'):
        raise ValueError('missing label-free state/history signature')
    return [('state', r['state_key']), ('history', r['history_key']), ('QF1', feature_signature(r))]


def make_mask(rows):
    ids, family_splits, game_splits = set(), {}, {}
    for r in rows:
        if any(k in r for k in ('rootmean', 'z', 'z_stm', 'loss', 'rootNN', 'winner')):
            raise ValueError('labels prohibited in exposure-mask input')
        if r['id'] in ids or r['split'] not in ('train', 'validation', 'test'):
            raise ValueError('duplicate ID or invalid partition')
        ids.add(r['id'])
        for seen, key in [(family_splits, r['group']), (game_splits, r.get('game_id', r['group']))]:
            if key in seen and seen[key] != r['split']:
                raise ValueError('game/family crosses partition')
            seen[key] = r['split']
    train = {s for r in rows if r['split'] == 'train' for s in signatures(r)}
    tv = train | {s for r in rows if r['split'] == 'validation' for s in signatures(r)}
    masks = {}
    groups = {}
    for r in rows:
        shared = [] if r['split'] == 'train' else [s[0] for s in signatures(r) if s in (train if r['split'] == 'validation' else tv)]
        masks[r['id']] = {'primary_eligible': not shared, 'exposure': sorted(set(shared)), 'split': r['split'], 'group': r['group']}
        g = groups.setdefault(r['group'], {'split': r['split'], 'rows': 0, 'eligible': 0})
        g['rows'] += 1
        g['eligible'] += not shared
    return {'rule': 'state OR history OR STM-QF1 input sharing; max-train96 fixed before selection',
            'rows': masks, 'games': groups, 'feature_version': 'QF1', 'labels_used': False,
            'zero_eligible_games': sorted(g for g, v in groups.items() if not v['eligible'])}


def load_stage(path):
    m = json.loads(Path(path).read_text())
    if m.get('kind') != 'QF1-training-stage':
        raise ValueError('training manifest kind')
    meta = read_rows(bound_path(m, 'metadata'))
    mask = json.loads(bound_path(m, 'mask').read_text())
    labels = read_rows(bound_path(m, 'training_labels'))
    # Any test-labelled entry in the training label artifact is a hard error.
    if any(r.get('split') not in ('train', 'validation') for r in labels):
        raise ValueError('test labels prohibited in training artifact')
    by_id = {r['id']: r for r in labels}
    if len(by_id) != len(labels):
        raise ValueError('duplicate training label ID')
    selected = []
    for r in meta:
        if r['split'] == 'test' or (r['split'] == 'train' and r['group'] not in m['train_groups']):
            continue
        lab = by_id.get(r['id'])
        if lab is None:
            raise ValueError('missing train/validation label')
        if lab['split'] != r['split']:
            raise ValueError('label partition mismatch')
        if mask['rows'][r['id']]['split'] != r['split'] or mask['rows'][r['id']]['group'] != r['group']:
            raise ValueError('mask identity mismatch')
        selected.append({**r, 'rootmean': lab.get('rootmean'), 'z': lab.get('z'),
                         'primary_eligible': mask['rows'][r['id']]['primary_eligible']})
    return selected, m
