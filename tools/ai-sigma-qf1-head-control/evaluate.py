"""Read-only 200 evaluator reuse with bounded 204-only AST adaptations.

No source copy: only the function AST is compiled in memory. Distance is an
analytical baseline; its real initial NN parity was measured in training step0.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

D = Path('research-data/ai-sigma/frame14-head-control')
SOURCE = Path('tools/ai-sigma-qf1-distance-residual/evaluate.py')
SOURCE_SHA = 'b57bae032ea7f6d2702fe33380853fccfdbe40c2fe3b332a9e8739faa7391d3f'


def adapted():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    sys.path.insert(0, str(SOURCE.parent.resolve()))
    spec = importlib.util.spec_from_file_location('readonly_test_evaluator', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.D = D
    tree = ast.parse(SOURCE.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'evaluate')
    edits = {'analytical_identity': 0, 'identity_label': 0, 'bootstrap_seed': 0, 'unique_cap': 0}
    class Adapt(ast.NodeTransformer):
        def visit_Subscript(self, node):
            self.generic_visit(node)
            if isinstance(node.value, ast.Name) and node.value.id == 'predictions' and isinstance(node.slice, ast.Constant) and node.slice.value == 'distance_initial':
                node.slice.value = 'distance_only'
                edits['analytical_identity'] += 1
            return node
        def visit_Constant(self, node):
            if node.value == 'distance_initial_maxabs':
                node.value = 'analytical_distance_identity_maxabs'
                edits['identity_label'] += 1
            elif node.value == 20080311:
                node.value = 20480311
                edits['bootstrap_seed'] += 1
            return node
        def visit_Compare(self, node):
            self.generic_visit(node)
            if ast.unparse(node) == 'len(unique) <= 4':
                node.comparators[0].value = 3
                edits['unique_cap'] += 1
            return node
    function = Adapt().visit(function)
    assert edits == dict.fromkeys(edits, 1), edits
    compiled = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(compiled, str(SOURCE)+' [204 in-memory adaptation]', 'exec'), module.__dict__)
    return module.evaluate, edits


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--freeze')
    p.add_argument('--freeze-sha')
    p.add_argument('--samples', type=int)
    p.add_argument('--preflight', action='store_true')
    a = p.parse_args()
    evaluate, edits = adapted()
    if a.preflight:
        result = {'PASS': True, 'NN': 0, 'test_labels_read': False, 'source_SHA': SOURCE_SHA,
                  'exact_AST_edits': edits, 'bootstrap_seed': 20480311, 'unique_cap': 3,
                  'initial_NN_parity_reference': str(D/'finite-schema.json'),
                  'analytical_baselines_forward': 0}
        (D/'evaluator-preflight.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
    else:
        assert a.freeze and a.freeze_sha and a.samples
        f = json.loads(Path(a.freeze).read_text())
        assert f['bootstrap_seed'] == 20480311 and f['unique_NN_max'] == 3
        assert set(f['artifacts']) == {'candidate', 'best', 'last'}
        evaluate(a)
