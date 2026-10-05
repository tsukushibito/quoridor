"""Future authorized training entry; uses shared loader, never loads a model.

The preparation CLI never calls this module on real labels. Its small software
fixture uses synthetic train/validation labels only. Test labels are forbidden.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/nnue-training'))
import frame14_data as shared
from manifest_adapter import VERSION, require, row_schema


def load_training_stage(path):
    m = json.loads(Path(path).read_text())
    require(m.get('adapter_version') == VERSION, 'private adapter version')
    metadata = shared.read_rows(shared.bound_path(m, 'metadata'))
    mask = json.loads(shared.bound_path(m, 'mask').read_text())
    require(mask.get('plan_sha256') == m['plan_sha256'] and
            mask.get('largest_train_families') == m['largest_train_family_count'],
            'frozen maximum-mask binding')
    require(len(m['train_groups']) == m['train_family_count'] and
            len(set(m['train_groups'])) == len(m['train_groups']), 'stage family count')
    seen = set()
    allowed_labels = {}
    for r in metadata:
        row_schema(r)
        require(r['id'] not in seen, 'duplicate metadata ID')
        seen.add(r['id'])
        require(r['id'] in mask['rows'] and mask['rows'][r['id']]['split'] == r['split'] and
                mask['rows'][r['id']]['group'] == r['group'], 'missing/mismatched mask row')
        if r['split'] != 'test':
            allowed_labels[r['id']] = r['split']
    require(set(mask['rows']) == seen, 'extra/missing frozen mask row')
    for f in m['train_groups']:
        require(f in mask['games'] and mask['games'][f]['split'] == 'train', 'stage family assignment')
    labels = shared.read_rows(shared.bound_path(m, 'training_labels'))
    label_ids = set()
    for r in labels:
        require(r.get('id') in allowed_labels and r.get('split') == allowed_labels[r['id']],
                'test/unknown/misassigned training label')
        require(r['id'] not in label_ids, 'duplicate training label ID')
        label_ids.add(r['id'])
        for k in ('rootmean', 'z'):
            v = r.get(k)
            require(v is None or (type(v) in (int, float) and -1 <= v <= 1), 'target schema')
    require(label_ids == set(allowed_labels), 'missing maximum-train/validation label')
    rows, manifest = shared.load_stage(path)
    require(not any(r['split'] == 'test' for r in rows), 'test join prohibited')
    return rows, {**manifest, 'labels_verified_for_training': True,
                  'planned_partition_games': mask['planned_partition_games'],
                  'planned_partition_families': mask['planned_partition_families'],
                  'zero_row_families': sorted(f for f, g in mask['games'].items() if not g['rows']),
                  'zero_eligible_validation_families': sorted(f for f, g in mask['games'].items()
                                                             if g['split'] == 'validation' and not g['eligible'])}
