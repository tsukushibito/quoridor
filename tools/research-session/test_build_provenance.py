"""379 owning Git/Cargo/image discriminators. Synthetic executor, no native/model calls.

The outer software job owns resource/lifetime guards. Git fixture operations are
real standard Git; returned Cargo/job facts below are explicitly synthetic.
"""

import subprocess
import unittest

import test_lifecycle as fixture

lc = fixture.lc


class BuildProvenanceTests(unittest.TestCase):
    # Reuse existing fixture helpers, without inheriting/replaying its test methods.
    setUp = fixture.LifecycleTests.setUp
    file = fixture.LifecycleTests.file
    json = fixture.LifecycleTests.json
    intent = fixture.LifecycleTests.intent
    executor = fixture.LifecycleTests.executor
    build = fixture.LifecycleTests.build
    finalize = fixture.LifecycleTests.finalize
    origin = fixture.LifecycleTests.origin
    job = fixture.LifecycleTests.job

    def test_build379_standard_git_revision_delta_and_untracked_input(self):
        lc.source_check(self.source_info)
        self.source.write_bytes(b"fn materially_changed() { assert!(true); }\n")
        with self.assertRaisesRegex(lc.Refused, "Git delta drift"):
            lc.source_check(self.source_info)
        delta = subprocess.check_output(
            [
                "git",
                "-C",
                str(self.root),
                "diff",
                "--binary",
                "--no-ext-diff",
                "--no-textconv",
                "HEAD",
                "--",
            ]
        )
        self.source_info["patch"] = self.file("source-delta.patch", delta)
        self.source_info["patch"] = fixture.ref(self.source_info["patch"])
        lc.source_check(self.source_info)
        extra = self.file(
            "games/quoridor/crates/new_module.rs", b"fn actual_untracked_input() {}\n"
        )
        with self.assertRaisesRegex(lc.Refused, "untracked Cargo inputs drift"):
            lc.source_check(self.source_info)
        self.source_info["untracked_inputs"] = [fixture.ref(extra)]
        lc.source_check(self.source_info)
        othello = self.file("games/othello/crates/new_module.rs", b"fn othello_input() {}\n")
        with self.assertRaisesRegex(lc.Refused, "untracked Cargo inputs drift"):
            lc.source_check(self.source_info)
        self.source_info["untracked_inputs"].append(fixture.ref(othello))
        lc.source_check(self.source_info)
        extra.write_bytes(b"fn untracked_drift() {}\n")
        with self.assertRaises(lc.Refused):
            lc.source_check(self.source_info)
        wrong = dict(self.source_info, commit="0" * 40)
        with self.assertRaisesRegex(lc.Refused, "Git revision drift"):
            lc.source_check(wrong)

    def test_build379_cargo_receipt_single_image_and_normal_owning_completion(self):
        candidate = self.build()
        self.assertNotIn("compiled_sources", candidate)
        self.assertEqual(
            {r["role"] for r in candidate["checks"]},
            {"version", "test", "lint", "build"},
        )
        self.assertTrue(all("research-bindings" not in argv for argv in self.calls))
        result = self.finalize(self.root / "operation", self.job(candidate))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(result["cargo_artifact"]["target"]["name"], "quoridor-runner")
        self.assertEqual(
            lc.accepted_build(fixture.ref(self.root / "operation/manifest.json"))["artifact"],
            fixture.ref(self.private),
        )

    def test_build379_artifact_or_returned_capture_drift_cannot_complete(self):
        candidate = self.build()
        candidate["checks"][-1]["capture_complete"] = False
        (self.root / "operation/candidate.json").write_text(lc.json.dumps(candidate))
        result = self.finalize(self.root / "operation", self.job(candidate))
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any(e["stage"] == "command_return" for e in result["secondary"]))
        self.assertNotIn("compiled_sources", result)
        with self.assertRaises(lc.Refused):
            lc.accepted_build(fixture.ref(self.root / "operation/manifest.json"))

    def test_build379_private_artifact_drift_is_failed_not_reused(self):
        candidate = self.build()
        self.private.write_bytes(self.private.read_bytes() + b"changed image")
        result = self.finalize(self.root / "operation", self.job(candidate))
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["cleanup_complete"])
        self.assertTrue(any(e["stage"] == "final_artifact_source" for e in result["secondary"]))
        self.assertEqual(candidate["artifact"], result["artifact"])
        with self.assertRaises(lc.Refused):
            lc.accepted_build(fixture.ref(self.root / "operation/manifest.json"))

    def test_build379_obsolete_inventory_and_echo_role_refuse_before_child(self):
        bad = dict(
            self.source_info,
            compiled_sources={"second-authority": fixture.ref(self.source)},
        )
        with self.assertRaisesRegex(lc.Refused, "Git/Cargo source record"):
            lc.source_metadata_check(bad)
        self.spec["commands"].append(
            {
                "name": "obsolete",
                "role": "bindings",
                "argv": [str(self.private), "research-bindings"],
            }
        )
        with self.assertRaises(lc.Refused):
            lc.build_check(self.spec)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
