"""Metadata subset/cache boundary on actual modules; no model or numerical library."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from .common import DEFAULTS, validate_mixture_config
from .public_replay import training_view_indices

view_indices = training_view_indices
config_ns = dict(DEFAULTS=DEFAULTS, validate_mixture_config=validate_mixture_config)


class TrainingViewMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="training-view-NN0-")
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "view.json"
        self.cache = "c" * 64
        # Actual configured-cap T candidates, with fake V/unselected rows omitted.
        self.candidates = [0, 2, 4, 6]

    def write(self, value):
        self.file.write_text(json.dumps(value))
        b = self.file.read_bytes()
        return dict(
            path=str(self.file),
            sha256=hashlib.sha256(b).hexdigest(),
            bytes=len(b),
            mode=f"{self.file.stat().st_mode & 511:04o}",
        )

    def test_absent_and_valid_bound_subset_keep_existing_order(self):
        self.assertIs(view_indices(None, self.cache, self.candidates), self.candidates)
        ref = self.write(dict(cache_manifest_sha256=self.cache, indices=[2, 6]))
        self.assertEqual(view_indices(ref, self.cache, self.candidates), [2, 6])

    def test_wrong_cache_V_cap_and_malformed_indices_refuse(self):
        values = [
            dict(cache_manifest_sha256="d" * 64, indices=[2]),
            dict(cache_manifest_sha256=self.cache, indices=[1]),  # V
            dict(cache_manifest_sha256=self.cache, indices=[8]),  # outside configured view
            dict(cache_manifest_sha256=self.cache, indices=[]),
            dict(cache_manifest_sha256=self.cache, indices=[2, 2]),
            dict(cache_manifest_sha256=self.cache, indices=[6, 2]),
            dict(cache_manifest_sha256=self.cache, indices=[True]),
            dict(cache_manifest_sha256=self.cache, indices=[2.0]),
            dict(cache_manifest_sha256=self.cache, indices=["2"]),
            dict(cache_manifest_sha256=self.cache, indices=[-1]),
            dict(cache_manifest_sha256=self.cache, indices=[[2]]),
            dict(cache_manifest_sha256=self.cache, indices=[2], extra=1),
            None,
        ]
        for value in values:
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                view_indices(self.write(value), self.cache, self.candidates)
        ref = self.write(dict(cache_manifest_sha256=self.cache, indices=[4]))
        with self.assertRaises(ValueError):
            view_indices(ref, self.cache, [0, 2, 6])

    def test_view_FileRef_SHA_size_and_symlink_custody_refuse(self):
        ref = self.write(dict(cache_manifest_sha256=self.cache, indices=[2]))
        for key, value in [
            ("sha256", "0" * 64),
            ("bytes", ref["bytes"] + 1),
            ("bytes", 4 * 1024**2 + 1),
        ]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                view_indices({**ref, key: value}, self.cache, self.candidates)
        self.file.write_text("changed")
        with self.assertRaises(ValueError):
            view_indices(ref, self.cache, self.candidates)
        ref = self.write(dict(cache_manifest_sha256=self.cache, indices=[2]))
        link = Path(self.tmp.name) / "alias"
        link.symlink_to(self.file)
        with self.assertRaises(ValueError):
            view_indices({**ref, "path": str(link)}, self.cache, self.candidates)

    def test_optional_config_old_no_view_and_independent_byte_limits(self):
        cfg = copy.deepcopy(config_ns["DEFAULTS"])
        cfg["training"].update(target="z", steps=2, batch_size=8, reflection_probability=0)
        fake = dict(path="/FAKE/metadata", sha256="a" * 64, bytes=1, mode="0644")
        m = dict(
            train_family_row_cap=None,
            train_stock_strata=None,
            added_rows=8,
            public_rows=0,
            added_exposures=8,
            added_sampling_seed=1,
            public_sampling_seed=2,
            added_reflection_probability=0.5,
            added_reflection_seed=3,
            public_reflection_probability=0.5,
            public_reflection_seed=4,
            diagnostic_seed=5,
            public_membership=fake,
            public_acceptance=fake,
            selector=dict(public_non_regression=False, added_metric="family_mse"),
            output_limit_bytes=1048576,
            training_rows=16,
            public_file_decay=None,
            public_evaluation=None,
            public_acceptance_seed=None,
        )
        cfg["mixture"] = copy.deepcopy(m)
        original = copy.deepcopy(cfg)
        validate = config_ns["validate_mixture_config"]
        validate(cfg, dict(mixture=m))
        self.assertEqual(cfg, original)
        cfg["mixture"]["training_view"] = {**fake, "bytes": 2 * 1024**2}
        validate(cfg, dict(mixture=cfg["mixture"]))
        cfg["mixture"]["training_view"]["bytes"] = 4 * 1024**2 + 1
        with self.assertRaises(ValueError):
            validate(cfg, dict(mixture=cfg["mixture"]))
        cfg["mixture"]["training_view"] = None
        cfg["mixture"]["public_membership"] = {**fake, "bytes": 1024**2 + 1}
        with self.assertRaises(ValueError):
            validate(cfg, dict(mixture=cfg["mixture"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
