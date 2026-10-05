"""NN0 checks of a proposed sampling table; does not create Quoridor states."""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

DATA = Path('research-data/ai-sigma/frame10-gap-sampling')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def step(x):
    x = (x ^ (x << 13)) & 0xffffffff
    x = (x ^ (x >> 17)) & 0xffffffff
    return (x ^ (x << 5)) & 0xffffffff


def score_interval(scores):
    # Each prefix remains in its fixed denominator, including missing colors.
    return [sum(0 if x is None else x for x in scores) / 2,
            sum(1 if x is None else x for x in scores) / 2]


def main():
    raw = (DATA / 'recommended-seeds.json').read_bytes()
    table = json.loads(raw)
    slots = table['slots']
    assert len(slots) == 32
    assert Counter(s['layer_ply'] for s in slots) == {4: 8, 5: 8, 12: 8, 13: 8}
    assert [s['slot'] for s in slots] == list(range(1, 33))
    all_seeds = []
    for b in range(8):
        group = slots[4*b:4*b+4]
        order = sorted([4, 5, 12, 13], key=lambda L: hashlib.sha256(
            f'frame10-gap-order-v1|61041|{b}|{L}'.encode()).digest())
        assert [s['layer_ply'] for s in group] == order
        for s in group:
            assert s['candidate_color_order'] == ([1, 2] if b % 2 == 0 else [2, 1])
            assert s['search_seed_both'] == 1979
            expected = [int.from_bytes(hashlib.sha256(
                f'frame10-gap-prefix-v1|61041|L{s["layer_ply"]}|slot{b}|attempt{a}'.encode()
            ).digest()[:4], 'big') or 1 for a in range(8)]
            assert s['attempt_seeds'] == expected
            all_seeds.extend(expected)
    assert len(set(all_seeds)) == 256
    for L in [4, 5, 12, 13]:
        assert Counter(s['candidate_color_order'][0] for s in slots if s['layer_ply'] == L) == {1: 4, 2: 4}
    fixtures = [[0, 0], [1, 1], [1, 0], [0, 1], [.5, .5], [1, None], [0, None], [None, None]]
    expected = [[0, 0], [1, 1], [.5, .5], [.5, .5], [.5, .5], [.5, 1], [0, .5], [0, 1]]
    assert [score_interval(s) for s in fixtures] == expected
    prior = Path('research-data/ai-sigma/119-diverse-prefix/preregister.json')
    old_raw = prior.read_bytes()
    old = json.loads(old_raw)
    excluded = [{'ply': p['prefix_ply'], 'key': p['key']} for p in old['pairs']]
    assert len(excluded) == 8
    # This consumes no RuleA/NN/old WDL and does not select seeds by resulting balance.
    naive = Counter('pawn' if step(x) < 2**31 else 'wall' for x in range(61001, 61033))
    hashed = Counter('pawn' if step(s['attempt_seeds'][0]) < 2**31 else 'wall' for s in slots)
    plies = sum(2*(200-s['layer_ply']) for s in slots)
    result = {
        'issue': 'quoridor-4lc.148', 'status': 'static checks passed; proposal only',
        'table_sha256': sha(raw), 'seed_count': 256, 'unique_seed_count': 256,
        'legal_states_generated': 0, 'NN': 0, 'Chrome': 0, 'games': 0,
        'planned_prefix_units': 32, 'planned_games': 64, 'max_new_plies': plies,
        'nominal_thought_seconds': plies*.5, 'proposed_job_cap_seconds': 32*240,
        'overhead_headroom_seconds': 32*240-plies*.5,
        'conditional_independent_slot_hoeffding': {
            'one_sided_95_width': math.sqrt(math.log(20)/(2*32)),
            'two_sided_95_width': math.sqrt(math.log(40)/(2*32)),
            'formal_coverage_claim': False},
        'integer_only_first_class_probe': {'naive_consecutive': dict(naive), 'fixed_hash_derived': dict(hashed)},
        'paired_score_fixtures': [{'scores': s, 'interval': v} for s, v in zip(fixtures, expected)],
        'uniform_old_signature_exclusion': {'source': str(prior), 'sha256': sha(old_raw), 'signatures': excluded,
            'old_WDL_read_for_exclusion': False},
        'missing_policy': 'retain fixed 32 prefix denominator; unknown color interval [0,1]',
        'new_duplicate_policy': 'retain and flag; no replenishment',
    }
    (DATA / 'static-results.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'checks': 'pass', 'new_legal_states': 0, 'NN': 0, 'result_sha256': sha((DATA/'static-results.json').read_bytes())}))


if __name__ == '__main__':
    main()
