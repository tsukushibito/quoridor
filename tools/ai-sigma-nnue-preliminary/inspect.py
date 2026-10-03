"""Read four preregistered saved root records; no rule replay or NN execution."""
import hashlib
import json
import re
import struct
from pathlib import Path

D = Path('research-data/ai-sigma/154-nnue-preliminary')
TOKENS = re.compile(r'[{}\[\]"]')
DECODER = json.JSONDecoder()


def skip(s, i):
    while s[i].isspace():
        i += 1
    if s[i] == '"':
        return DECODER.raw_decode(s, i)[1]
    if s[i] not in '[{':
        j = i
        while j < len(s) and s[j] not in ',}]':
            j += 1
        return j
    depth, j = 1, i+1
    while depth:
        m = TOKENS.search(s, j)
        if not m:
            raise ValueError('unterminated JSON')
        if m[0] == '"':
            j = DECODER.raw_decode(s, m.start())[1]
        else:
            depth += 1 if m[0] in '[{' else -1
            j = m.end()
    return j


def fields(s, i):
    assert s[i] == '{'
    i += 1
    while True:
        while s[i].isspace() or s[i] == ',':
            i += 1
        if s[i] == '}':
            return
        name, j = DECODER.raw_decode(s, i)
        while s[j].isspace() or s[j] == ':':
            j += 1
        end = skip(s, j)
        yield name, j, end
        i = end


def first_item(s, i):
    assert s[i] == '['
    i += 1
    while s[i].isspace():
        i += 1
    return None if s[i] == ']' else (i, skip(s, i))


def main():
    selection = json.loads((D/'sample-selection.json').read_text())
    path = Path(selection['raw_parent'])/'browser-result.json'
    raw = path.read_bytes()
    s = raw.decode()
    rows_start = next(a for k, a, b in fields(s, 0) if k == 'rows')
    wanted = [(v.split('/')[0], v.split('/')[1]) for v in selection['selection_before_read']]
    fixtures_path = Path('research-data/ai-sigma/151-sigma-web-port/stageA-inputs.json')
    fixtures = {f['id']: f for f in json.loads(fixtures_path.read_bytes())['fixtures']}
    j = rows_start+1
    results = []
    while j < len(s):
        while s[j].isspace() or s[j] == ',':
            j += 1
        if s[j] == ']':
            break
        end = skip(s, j)
        spans = {k: (a, b) for k, a, b in fields(s, j)}
        scalar = lambda k: json.loads(s[slice(*spans[k])]) if k in spans else None
        key = (scalar('fixture_id'), scalar('engine'))
        if key in wanted:
            cp = scalar('cp') or {}
            numeric_span = first_item(s, spans['numeric'][0]) if 'numeric' in spans else None
            numeric = json.loads(s[slice(*numeric_span)]) if numeric_span else {}
            f = fixtures[key[0]]
            board = f.get('board', {})
            N = cp.get('root_visits', cp.get('simulations'))
            S = cp.get('root_valueSum')
            mean = cp.get('root_mean')
            parity = None if mean is None or S is None or not N else abs(mean-S/N) < 1e-12
            root_path = numeric.get('path')
            # Exact root feature comparison is saved arithmetic, not new encoding.
            expected = f.get('features_bits')
            if expected is None and 'raw_features_float32' in f:
                expected = [struct.unpack('<I', struct.pack('<f', x))[0] for x in f['raw_features_float32']]
            bits = numeric.get('features_bits')
            bit_equal = None if expected is None or bits is None else expected == bits
            r = {'fixture': key[0], 'engine': key[1], 'K': scalar('K'),
                 'classification': f.get('classification'), 'legal_prefix_length': len(f.get('legal_prefix', [])),
                 'board_fields': sorted(board), 'full_legal_prefix_saved': 'legal_prefix' in f,
                 'fixture_history_saved': 'history_counts' in f, 'root_record_fields': sorted(numeric),
                 'root_path': root_path, 'root_record_really_root': root_path == [],
                 'features_count': len(bits) if bits else None, 'fixture_root_features_exact': bit_equal,
                 'root_side': numeric.get('turn'), 'root_key_saved': 'key' in numeric,
                 'root_history_saved': 'history' in numeric, 'root_total_ply_saved': 'ply' in numeric,
                 'root_NN_value_side_to_move': numeric.get('value'), 'root_visits': N,
                 'root_valueSum': S, 'root_mean_side_to_move': mean, 'root_mean_sum_N_parity': parity,
                 'game_outcome': 'missing: StageA search, not game',
                 'actual_NN_calls': cp.get('nn_calls'), 'terminal_noNN': scalar('terminal_noNN'),
                 'visits_policy': 'available root_edges visit field; not value target',
                 'source_span_sha256': hashlib.sha256(s[j:end].encode()).hexdigest(),
                 'copied_deep_payload': False}
            if numeric.get('turn') in (0, 1):
                sign = 1 if numeric['turn'] == 0 else -1
                r['NN_value_P1'] = sign*numeric['value'] if numeric.get('value') is not None else None
                r['root_mean_P1'] = sign*mean if mean is not None else None
            results.append(r)
        j = end
    assert len(results) <= 4
    out = {'issue': 'quoridor-4lc.154', 'run': 'schema-r1', 'samples': results,
           'selected_missing': [list(k) for k in wanted if k not in [(r['fixture'], r['engine']) for r in results]],
           'raw_path': str(path), 'raw_sha256': hashlib.sha256(raw).hexdigest(),
           'fixture_path': str(fixtures_path), 'fixture_sha256': hashlib.sha256(fixtures_path.read_bytes()).hexdigest(),
           'raw_after_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'new_NN_Chrome_build_game_training': 0, 'new_rule_replay': 0,
           'signature': 'root key/history/ply/side retained; board and wall remaining in input fixture',
           'teacher_ready_claim': False}
    assert out['raw_sha256'] == out['raw_after_sha256']
    (D/'schema-results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
