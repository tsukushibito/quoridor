"""New source-reflection domain wiring test, NN0; no former suites replayed."""

import argparse
import json
from pathlib import Path
import sys
import unittest


class ReflectionDomains(unittest.TestCase):
    def test_shared_seed_independent_jump_and_added_prefix_nn0(self):
        import numpy as np
        from quoridor_training.public_replay import reflection_generators

        settings = {"added_reflection_seed": 31, "public_reflection_seed": 31}
        a, p = reflection_generators(settings)
        a2, p2 = reflection_generators(settings)
        prefix = a.random(15)
        p2.random(103)
        split = np.concatenate([a2.random(3), a2.random(12)])
        self.assertTrue(np.array_equal(prefix, split))
        self.assertFalse(np.array_equal(prefix, p.random(15)))
        self.assertTrue(np.array_equal(prefix, np.random.default_rng(31).random(15)))
        self.assertTrue(
            np.array_equal(
                p2.random(5), np.random.Generator(np.random.PCG64(31).jumped()).random(108)[-5:]
            )
        )
        self.assertEqual((prefix < 0).sum(), 0)
        self.assertEqual((prefix < 1).sum(), 15)
        a3, p3 = reflection_generators({"added_reflection_seed": 31, "public_reflection_seed": 99})
        self.assertTrue(np.array_equal(a3.random(15), prefix))
        self.assertFalse(np.array_equal(p3.random(15), prefix))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    import quoridor_training

    quoridor_training.__path__.insert(0, str(args.source))
    sys.modules.pop("quoridor_training.public_replay", None)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReflectionDomains)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forwards": 0,
                "actual_fit_updates": 0,
                "synthetic_rng_only": True,
                "errors": [s for _, s in result.errors],
                "failures": [s for _, s in result.failures],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
