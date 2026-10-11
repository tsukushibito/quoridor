"""One synthetic BUILD pre-copy definition; no actual compiler/artifact/model calls."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(os.environ.get("ARENA_361_MAIN_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / "python"))
SOURCE = Path(os.environ.get("ARENA_361_LIFECYCLE", ROOT / "scripts/dev/research-lifecycle.py"))
module = importlib.util.spec_from_file_location("private361_lifecycle", SOURCE)
lc = importlib.util.module_from_spec(module)
module.loader.exec_module(lc)


class PrivateCopyTests(unittest.TestCase):
    def test_real_pre_copy_refusal_and_small_copy_preserve_other_domain(self):
        # All handover values/assets are synthetic accounting, never actual Root custody.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "fresh"
            private.mkdir()
            source = root / "FAKE_NOT_EXECUTABLE"
            raw = b"small synthetic compiler artifact; no engine/model/ELF"
            source.write_bytes(raw)
            source.chmod(0o644)
            destination = private / "candidate"
            hpath = root / "handover.json"
            h = {
                "fresh_private_root": str(private),
                "fresh_private_forward_max_B": 16 * 1024**2,
                "private_candidate_upper_B": 12 * 1024**2,
                "private_pool_B": 32 * 1024**2,
                "old_private_retained_allocated_B": 16 * 1024**2,
            }
            spec = {"owner": str(root), "target": str(root), "private": str(destination)}

            def bind(value):
                hpath.write_text(json.dumps(value))
                spec["target_handover"] = lc.bound(hpath)[0]

            block = os.statvfs(private).f_frsize
            prospective = lc.allocated(private) + ((len(raw) + block - 1) // block) * block + 65536
            cases = (
                ({**h, "fresh_private_root": str(root / "wrong")}, "fresh private root"),
                ({**h, "private_candidate_upper_B": len(raw) - 1}, "candidate size"),
                (
                    {
                        **h,
                        "private_candidate_upper_B": len(raw),
                        "fresh_private_forward_max_B": prospective - 1,
                    },
                    "fresh private room",
                ),
                (
                    {
                        **h,
                        "old_private_retained_allocated_B": h["private_pool_B"] - prospective + 1,
                    },
                    "selected private group room",
                ),
            )
            for changed, error in cases:
                with self.subTest(error=error):
                    bind(changed)
                    original_handover = hpath.read_bytes()
                    with self.assertRaisesRegex(lc.Refused, error):
                        lc.private_copy_check(spec, source)
                    self.assertFalse(destination.exists())
                    self.assertEqual(list(private.iterdir()), [])
                    self.assertEqual(source.read_bytes(), raw)
                    self.assertEqual(hpath.read_bytes(), original_handover)
                    self.assertEqual(lc.document(spec["target_handover"]), changed)
            bind(h)
            original_handover = hpath.read_bytes()
            lc.private_copy_check(spec)  # The same check used by build_check.
            lc.private_copy_check(spec, source)  # Immediately precedes unchanged copy_artifact.
            result = lc.copy_artifact(source, destination)
            self.assertEqual(destination.read_bytes(), raw)
            self.assertEqual(result, lc.bound(destination)[0])
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["mode"], "0644")
            self.assertEqual(hpath.read_bytes(), original_handover)
            self.assertEqual(
                lc.document(spec["target_handover"])["old_private_retained_allocated_B"],
                16 * 1024**2,
            )


if __name__ == "__main__":
    unittest.main()
