"""Changed explicit model parity boundary; in-memory fixtures, no fit/artifacts."""

import io
import json
import unittest
from unittest.mock import patch

from othello_training import parity, pattern
from test_pattern_features import fixture, model


class PatternParity(unittest.TestCase):
    def test_explicit_model_and_state_lines_preserve_raw_score_provenance(self):
        weights, position = model(), fixture()
        states = [position, {**position, "toMove": 2}]
        output = io.StringIO()
        with (
            patch.object(parity.data, "bounded_bytes", return_value=json.dumps(weights).encode()),
            patch.object(
                parity.sys, "stdin", io.StringIO("\n".join(json.dumps(s) for s in states) + "\n")
            ),
            patch.object(parity.sys, "stdout", output),
        ):
            parity.main(["--model", "in-memory-validation-fixture"])
        observed = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(
            observed,
            [
                dict(score=pattern.evaluate(weights, s), scoreKind="heuristic", proven=False)
                for s in states
            ],
        )
        self.assertEqual(observed[0]["score"], -observed[1]["score"])

    def test_oversized_or_invalid_state_fails_instead_of_partial_score(self):
        for payload in [" " * 4097 + "\n", "{}\n"]:
            with (
                patch.object(
                    parity.data, "bounded_bytes", return_value=json.dumps(model()).encode()
                ),
                patch.object(parity.sys, "stdin", io.StringIO(payload)),
                self.assertRaises(ValueError),
            ):
                parity.main(["--model", "in-memory-validation-fixture"])


if __name__ == "__main__":
    unittest.main()
