"""New metadata-only domain definitions; source phase UNRUN, no model assets."""

import importlib.util
from pathlib import Path
import sys
import unittest


class Continuation360Sources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        spec = importlib.util.spec_from_file_location(
            "continuation360_publisher", root / "scripts/dev/research-lifecycle.py"
        )
        cls.publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.publisher)
        sys.path.insert(0, str(root / "python/quoridor_training/research355"))
        spec = importlib.util.spec_from_file_location(
            "continuation360_consumer",
            root / "python/quoridor_training/research355/lifecycle355.py",
        )
        cls.consumer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.consumer)

    def test_continuation360_exact_both_source_domains_and_digest_pairing(self):
        for keys in (self.publisher.RESEARCH_SOURCE_KEYS, self.publisher.RESEARCH_ORDERING_KEYS):
            qualified = {key: "a" * 64 for key in keys}
            native = {
                key: digest
                for key, digest in qualified.items()
                if key != "runner/sigma_qualification.rs"
            }
            before = (qualified.copy(), native.copy())
            self.publisher.generation_source_correspondence(native, qualified)
            self.consumer.generation_sources(native, qualified)
            self.assertEqual(
                self.consumer.compiled_digest(qualified), self.publisher.canonical_sha(qualified)
            )
            self.assertEqual(before, (qualified, native))
            self.assertEqual(len(qualified) - len(native), 1)

    def test_continuation360_missing_unknown_and_shared_drift_refuse(self):
        qualified = {key: "a" * 64 for key in self.publisher.RESEARCH_ORDERING_KEYS}
        native = {
            key: digest
            for key, digest in qualified.items()
            if key != "runner/sigma_qualification.rs"
        }
        for bad_native, bad_qualified in (
            (
                {key: value for key, value in native.items() if key != "ai/static_ordering.rs"},
                qualified,
            ),
            (
                native,
                {
                    key: value
                    for key, value in qualified.items()
                    if key != "ai/continuation_history.rs"
                },
            ),
            ({**native, "ai/unknown.rs": "a" * 64}, {**qualified, "ai/unknown.rs": "a" * 64}),
            ({**native, "ai/static_ordering.rs": "b" * 64}, qualified),
        ):
            with self.assertRaises(ValueError):
                self.publisher.generation_source_correspondence(bad_native, bad_qualified)
            with self.assertRaises(ValueError):
                self.consumer.generation_sources(bad_native, bad_qualified)

    def test_assessment360_conditional_caller_has_exact_research_only_projection(self):
        qualified = {key: "a" * 64 for key in self.publisher.RESEARCH_ASSESSMENT_KEYS}
        native = {
            key: value
            for key, value in qualified.items()
            if key not in {"runner/sigma_qualification.rs", "runner/ordering_assessment.rs"}
        }
        self.assertEqual(len(qualified), 38)
        self.assertEqual(len(native), 36)
        self.publisher.generation_source_correspondence(native, qualified)
        self.consumer.generation_sources(native, qualified)
        self.assertEqual(
            self.consumer.compiled_digest(qualified), self.publisher.canonical_sha(qualified)
        )
        # The caller is not a free unknown native key or an optional hash omission.
        for bad_native, bad_qualified in (
            ({**native, "runner/ordering_assessment.rs": "a" * 64}, qualified),
            (native, {**qualified, "runner/unknown.rs": "a" * 64}),
            ({**native, "ai/alphabeta.rs": "b" * 64}, qualified),
            (native, {**qualified, "runner/ordering_assessment.rs": "invalid"}),
        ):
            with self.assertRaises(ValueError):
                self.publisher.generation_source_correspondence(bad_native, bad_qualified)
            with self.assertRaises(ValueError):
                self.consumer.generation_sources(bad_native, bad_qualified)


if __name__ == "__main__":
    unittest.main()
