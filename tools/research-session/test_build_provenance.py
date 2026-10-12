"""379 owning Git/Cargo/image discriminators. Synthetic executor, no native/model calls.

The outer software job owns resource/lifetime guards. Git fixture operations are
real standard Git; returned Cargo/job facts below are explicitly synthetic.
"""

import copy
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
        extra = self.file("crates/new_module.rs", b"fn actual_untracked_input() {}\n")
        with self.assertRaisesRegex(lc.Refused, "untracked Cargo inputs drift"):
            lc.source_check(self.source_info)
        self.source_info["untracked_inputs"] = [fixture.ref(extra)]
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
            {r["role"] for r in candidate["checks"]}, {"version", "test", "lint", "build"}
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
            self.source_info, compiled_sources={"second-authority": fixture.ref(self.source)}
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


class RetainedOrderingTests(unittest.TestCase):
    """Metadata-only checks for the changed input/head reuse boundary."""

    def subjects(self):
        original = {
            "schema": lc.BUILD_SCHEMA,
            "status": "PASS",
            "cleanup_complete": True,
            "remaining": [],
            "source": {
                "workspace": "/synthetic376",
                "commit": "a" * 40,
                "manifest": {"sha256": "1" * 64},
                "lock": {"sha256": "2" * 64},
                "cargo_configs": [],
            },
            "artifact": {"sha256": "3" * 64},
            "tools": {
                "RUSTC": {
                    "file": {
                        "path": "/synthetic376/rustc",
                        "sha256": "7" * 64,
                        "bytes": 1,
                        "mode": "0755",
                    },
                    "version": "fixed native compiler",
                },
                "PYTHON": "3.11.2",
            },
            "env": {
                "RUSTFLAGS": "-C debuginfo=0",
                "CARGO_PROFILE_RELEASE_OPT_LEVEL": "3",
                "CARGO_PROFILE_RELEASE_DEBUG": "0",
                "TMPDIR": "/old-TMP",
            },
            "checks": [
                {
                    "role": role,
                    "argv": ["cargo", role],
                    "guardian_return": {"exit_code": 0, "cleanup_complete": True},
                }
                for role in ("test", "lint", "build")
            ],
        }
        current = copy.deepcopy(original)
        current["source"]["commit"] = "b" * 40
        current["artifact"]["sha256"] = "4" * 64
        current["tools"]["PYTHON"] = "3.14.7"
        current["env"]["TMPDIR"] = "/current-TMP"
        current["env"].update(
            CUDA_VISIBLE_DEVICES="",
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
            NUMEXPR_NUM_THREADS="1",
            ORT_DISABLE_TELEMETRY="1",
        )

        def reference(name):
            return {
                "path": f"/synthetic376/{name}/manifest.json",
                "sha256": "5" * 64,
                "bytes": 1,
                "mode": "0644",
            }

        qualification, original_ref = reference("qualification"), reference("original")
        cheap = {"algorithm": "unchanged selected cheap376 algorithm"}
        adoption = {
            "schema": "quoridor.research.source-adoption.v1",
            "status": "ACCEPTED",
            "source": copy.deepcopy(current["source"]),
            "retained_ordering_numerical": {
                "scope": "ordering20-input-and-head-v1",
                "qualification": qualification,
                "build_manifest": original_ref,
                "cheap_static376": cheap,
            },
        }
        return current, original, adoption, qualification, original_ref, cheap

    def test_ordering376_runtime_controller_changes_do_not_relabel_original_subject(self):
        current, original, adoption, qualification, original_ref, cheap = self.subjects()
        before = copy.deepcopy((original, qualification, original_ref))
        lc.retained_ordering_source(current, original, adoption, qualification, original_ref, cheap)
        self.assertEqual((original, qualification, original_ref), before)
        self.assertNotEqual(original["artifact"], current["artifact"])

    def test_ordering376_native_subject_and_trusted_adoption_drifts_refuse(self):
        subjects = self.subjects()
        for section, key in (
            ("tools", "RUSTC"),
            ("env", "RUSTFLAGS"),
            ("env", "CARGO_PROFILE_RELEASE_OPT_LEVEL"),
            ("env", "CARGO_PROFILE_RELEASE_DEBUG"),
        ):
            with self.subTest(section=section, key=key):
                current, original, adoption, qualification, original_ref, cheap = copy.deepcopy(
                    subjects
                )
                current[section][key] = "drift"
                with self.assertRaises(lc.Refused):
                    lc.retained_ordering_source(
                        current, original, adoption, qualification, original_ref, cheap
                    )
        # Current-only LTO leaves all prior facts and trusted references equal.
        current, original, adoption, qualification, original_ref, cheap = copy.deepcopy(subjects)
        current["env"]["CARGO_PROFILE_RELEASE_LTO"] = "fat"
        self.assertEqual(current["tools"], subjects[0]["tools"])
        self.assertEqual(current["checks"], subjects[0]["checks"])
        self.assertEqual(current["source"], subjects[0]["source"])
        self.assertEqual((adoption, qualification, original_ref, cheap), subjects[2:])
        with self.assertRaisesRegex(lc.Refused, "recorded native configuration changed"):
            lc.retained_ordering_source(
                current, original, adoption, qualification, original_ref, cheap
            )
        for channel in (
            "CARGO_ENCODED_RUSTFLAGS",
            "RUSTC_WRAPPER",
            "RUSTC_WORKSPACE_WRAPPER",
            "CARGO_BUILD_RUSTC_WRAPPER",
            "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER",
            "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS",
            "CARGO_BUILD_TARGET",
            "RUSTUP_TOOLCHAIN",
            "CARGO_NET_OFFLINE",
        ):
            for original_side in (False, True):
                for value in ("-Ctarget-cpu=native", ""):
                    with self.subTest(channel=channel, original_side=original_side, value=value):
                        current, original, adoption, qualification, original_ref, cheap = (
                            copy.deepcopy(subjects)
                        )
                        subject = original if original_side else current
                        subject["env"][channel] = value
                        with self.assertRaisesRegex(
                            lc.Refused, "recorded native configuration changed"
                        ):
                            lc.retained_ordering_source(
                                current, original, adoption, qualification, original_ref, cheap
                            )
        for section, key in (
            ("tools", "RUSTC"),
            ("env", "RUSTFLAGS"),
            ("env", "CARGO_PROFILE_RELEASE_OPT_LEVEL"),
            ("env", "CARGO_PROFILE_RELEASE_DEBUG"),
        ):
            for original_side in (False, True):
                with self.subTest(missing=key, original_side=original_side):
                    current, original, adoption, qualification, original_ref, cheap = copy.deepcopy(
                        subjects
                    )
                    subject = original if original_side else current
                    del subject[section][key]
                    with self.assertRaises(lc.Refused):
                        lc.retained_ordering_source(
                            current, original, adoption, qualification, original_ref, cheap
                        )
        for section, key, value in (
            ("tools", "RUSTC", "not a ToolRef"),
            ("env", "CARGO_PROFILE_RELEASE_LTO", None),
        ):
            with self.subTest(malformed_equal=key):
                current, original, adoption, qualification, original_ref, cheap = copy.deepcopy(
                    subjects
                )
                original[section][key] = current[section][key] = value
                with self.assertRaises(lc.Refused):
                    lc.retained_ordering_source(
                        current, original, adoption, qualification, original_ref, cheap
                    )
        for field in ("manifest", "lock", "cargo_configs"):
            with self.subTest(field=field):
                current, original, adoption, qualification, original_ref, cheap = copy.deepcopy(
                    subjects
                )
                current["source"][field] = "drift"
                adoption["source"] = copy.deepcopy(current["source"])
                with self.assertRaises(lc.Refused):
                    lc.retained_ordering_source(
                        current, original, adoption, qualification, original_ref, cheap
                    )
        for drift in (
            "release",
            "qualification",
            "old-build",
            "source",
            "algorithm",
            "scope",
            "old-status",
        ):
            with self.subTest(drift=drift):
                current, original, adoption, qualification, original_ref, cheap = copy.deepcopy(
                    subjects
                )
                if drift == "release":
                    current["checks"][-1]["argv"] = ["cargo", "different-release"]
                elif drift == "qualification":
                    adoption["retained_ordering_numerical"]["qualification"]["sha256"] = "6" * 64
                    qualification = copy.deepcopy(subjects[3])
                elif drift == "old-build":
                    adoption["retained_ordering_numerical"]["build_manifest"]["sha256"] = "6" * 64
                    original_ref = copy.deepcopy(subjects[4])
                elif drift == "source":
                    adoption["source"]["commit"] = "c" * 40
                elif drift == "algorithm":
                    adoption["retained_ordering_numerical"]["cheap_static376"] = {
                        "algorithm": "other"
                    }
                elif drift == "scope":
                    adoption["retained_ordering_numerical"]["scope"] = "other"
                else:
                    original["status"] = "FAILED"
                with self.assertRaises(lc.Refused):
                    lc.retained_ordering_source(
                        current, original, adoption, qualification, original_ref, cheap
                    )


if __name__ == "__main__":
    unittest.main()
