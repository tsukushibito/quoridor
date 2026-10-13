"""NN0 metadata: actual large cache JSON is separate from binary/model payloads."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_lifecycle import lc


class MixedCacheMetadata(unittest.TestCase):
    def test_large_manifest_uses_declared_bytes_and_still_refuses_custody_or_empty_split(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            added = root / "added"
            added.mkdir()
            warm = {
                "descriptor": {"path": "/synthetic/descriptor"},
                "weights": {"path": "/synthetic/weights"},
                "evaluator_sha256": "a" * 64,
                "optimizer": "fresh",
                "scale": "incumbent",
            }
            public = {"path": str(root / "public-index/cache.json")}
            acceptance = {"path": str(root / "acceptance.json")}
            cache = {
                "rows": 2,
                "stream_intake": {"status": "complete"},
                "sha256": {},
                "file_bytes": {},
                "common_corpus": {"common_eligible_by_split": {"train": 1, "validation": 1}},
                "preserved_chronological_ids": "x" * (lc.CONTROL_BYTES + 1),
            }
            binaries = []
            for name, width in lc.COMPACT_CACHE_WIDTHS.items():
                cache["sha256"][name] = "b" * 64
                cache["file_bytes"][name] = 2 * width
                binaries.append({"path": str(added / name), "sha256": "b" * 64, "bytes": 2 * width})
            cache_path = added / "cache.json"
            cache_path.write_text(json.dumps(cache))
            cache_ref = lc.bound(cache_path, cache_path.stat().st_size)[0]
            self.assertGreater(cache_ref["bytes"], lc.CONTROL_BYTES)
            config = {
                "training": {"target": "z"},
                "experiment": {"study": "mixed-outcome", "warm_start": warm},
                "mixture": {
                    "public_membership": public,
                    "public_acceptance": acceptance,
                },
            }
            config_ref = {"path": str(root / "config.json")}
            experiment = {
                "phase": "fit",
                "config": config_ref,
                "planned_slots": 0,
                "rules": "research-standard-2p-threefold-goal-first-v1",
                "distance_units": "wall-distance/80",
                "value_perspective": "side-to-move",
                "inputs": [public, acceptance, cache_ref, *binaries],
                "models": [{k: warm[k] for k in ("descriptor", "weights", "evaluator_sha256")}],
            }
            spec = {
                "data_root": str(root / "fit"),
                "argv": [
                    sys.executable,
                    "-B",
                    "-m",
                    "quoridor_training.train",
                    "train",
                    "--cache",
                    str(added),
                    "--output",
                    str(root / "fit"),
                    "--config",
                    config_ref["path"],
                ],
            }
            with (
                patch.object(lc, "document", return_value=config),
                patch.object(lc, "project_python", return_value=Path(sys.executable)),
                patch.object(lc, "project_interpreter"),
                patch.object(lc, "common_training_environment"),
                patch.object(lc, "numerical_check"),
            ):
                lc.common_study_check(spec, experiment, {}, {})
                binaries[0]["bytes"] += 1
                with self.assertRaisesRegex(lc.Refused, "binary custody"):
                    lc.common_study_check(spec, experiment, {}, {})
                binaries[0]["bytes"] -= 1
                cache["common_corpus"]["common_eligible_by_split"]["validation"] = 0
                cache_path.write_text(json.dumps(cache))
                experiment["inputs"][2] = lc.bound(cache_path, cache_path.stat().st_size)[0]
                with self.assertRaisesRegex(lc.Refused, "nonempty"):
                    lc.common_study_check(spec, experiment, {}, {})
