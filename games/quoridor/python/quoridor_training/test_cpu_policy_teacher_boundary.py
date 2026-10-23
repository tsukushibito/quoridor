"""One new zero-head metadata definition for saved C-only CPU admission."""

import copy
import json
import unittest
from unittest.mock import patch

from . import public_static_values as owner


class CpuPolicyTeacherBoundaryMetadata(unittest.TestCase):
    def test_saved_C_cpu_tuple_and_refusals_nn0(self):
        def fixture():
            def ref(name):
                return {
                    "path": "/synthetic-cpu/" + name,
                    "sha256": "a" * 64,
                    "bytes": 1,
                    "mode": "0644",
                }

            names = (
                "result",
                "execution",
                "completion",
                "stage",
                "teachers",
                "head_source",
                "encoder_library",
                "encoder_build",
                "encoder_closure",
            )
            refs = {name: ref(name) for name in names}
            model = ref("model")
            model["bytes"] = 28685398
            c20 = ref("c20")
            identity = [1, 2, 33188, model["bytes"], 3, 4]
            cfg = {
                "runtime_boundary": refs,
                "model": model,
                "model_identity": identity,
                "device": "cpu",
                "cpu_threads": 1,
                "c20_library": c20,
            }
            result = {
                "primary": None,
                "actual_fixed_encoder_boards": 2,
                "constructor_implicit_input_rows": 0,
                "source_input_comparison_sha256": "b" * 64,
                "records": {
                    "C": {
                        "constructor_entered": True,
                        "constructor_returned": True,
                        "input_rows": 2,
                        "finite_rows": 2,
                        "attempted_rows": 4,
                        "single_batch_pass": True,
                        "teacher_model": model,
                    }
                },
                "heads": {
                    "C": {
                        "kind": "claustrophobia",
                        "attempted_rows": 4,
                        "returned_finite_rows": 4,
                        "failed_attempt_rows": 0,
                        "constructor_forward_rows": 0,
                        "explicit_warmup_rows": 0,
                        "joint_policy_value_compute": True,
                        "label_semantics": "raw-local-stm-single-network-post-tanh",
                        "extra_tanh_sign_discount_rescaling": False,
                        "runtime": {
                            "device": "cpu",
                            "autocast": False,
                            "original_parameter_dtypes": ["torch.float32"],
                            "inference_dtype": "float32",
                        },
                    }
                },
            }
            argv = ["/synthetic/python", "-B", "/synthetic/qualified.py", "C"]
            execution = {
                "status": "RETURNED_COMPLETE",
                "primary": None,
                "remaining": [],
                "GPU": 0,
                "runtime": {"model_custody": [model]},
                "returned": {
                    "command": argv,
                    "status": "complete",
                    "exit_code": 0,
                    "primary_error": None,
                    "remaining": [],
                    "cleanup_complete": True,
                    "direct_child_reaped": True,
                    "handle_closes_complete": True,
                    "signal_mask_restoration": "completed",
                    "final_record_persist": "completed",
                    "finalization_errors": [],
                },
            }
            comparison = ref("comparison")
            comparison["sha256"] = "b" * 64
            data = {
                "result": result,
                "execution": execution,
                "completion": {
                    "refs": [refs["result"], refs["execution"]],
                    "observed": copy.deepcopy(result),
                },
                "stage": {
                    "argv": argv,
                    "model_custody": [model],
                    "fixed_small_refs": [
                        refs["teachers"],
                        refs["head_source"],
                        comparison,
                    ],
                    "finite_plan": {
                        "teachers_selected": ["C"],
                        "fixed_boards": 2,
                        "batch_plus_singles_per_teacher": 4,
                    },
                },
                "teachers": {
                    "teachers": [
                        {
                            "key": "C",
                            "adapter": "claustrophobia",
                            "model": model,
                            "identity": {"release_commit": "c" * 40},
                        }
                    ]
                },
                "head_source": "synthetic source, not imported",
                "encoder_library": {"artifact": c20},
                "encoder_build": {"closure": refs["encoder_closure"]},
                "encoder_closure": {"upstream_commit": "c" * 40},
            }

            def bound(reference, cap):
                name = reference["path"].rsplit("/", 1)[-1]
                raw = json.dumps(data[name]).encode()
                self.assertLessEqual(len(raw), cap)
                return raw

            return cfg, data, bound, identity

        cfg, data, bound, identity = fixture()
        with (
            patch.object(owner, "bound_file_bytes", bound),
            patch.object(owner, "file_identity", return_value=tuple(identity)),
        ):
            self.assertEqual(owner.cpu_policy_teacher_boundary(cfg), identity)

        cases = [
            (
                "flat-GPU-ingredient",
                lambda c, d: c.update(runtime_boundary={"status": "PASS_PER_TEACHER_BOUNDARIES"}),
            ),
            ("requested-GPU", lambda c, d: c.update(device="cuda:0")),
            (
                "observed-GPU",
                lambda c, d: d["result"]["heads"]["C"]["runtime"].update(device="cuda:0"),
            ),
            (
                "failed-primary",
                lambda c, d: d["result"].update(primary={"type": "Error"}),
            ),
            (
                "failed-return",
                lambda c, d: d["execution"]["returned"].update(exit_code=1),
            ),
            (
                "pending-return",
                lambda c, d: d["execution"]["returned"].update(signal_mask_restoration="pending"),
            ),
            (
                "not-reaped",
                lambda c, d: d["execution"]["returned"].update(direct_child_reaped=False),
            ),
            (
                "model-mismatch",
                lambda c, d: c.update(model={**c["model"], "sha256": "d" * 64}),
            ),
            (
                "FP16",
                lambda c, d: d["result"]["heads"]["C"]["runtime"].update(inference_dtype="float16"),
            ),
            (
                "rescaling",
                lambda c, d: d["result"]["heads"]["C"].update(
                    extra_tanh_sign_discount_rescaling=True
                ),
            ),
            ("missing-result", lambda c, d: d["result"].pop("records")),
            (
                "failed-rows",
                lambda c, d: d["result"]["heads"]["C"].update(failed_attempt_rows=1),
            ),
            (
                "bool-count",
                lambda c, d: d["result"]["records"]["C"].update(input_rows=True),
            ),
            ("source-mismatch", lambda c, d: d["stage"].update(fixed_small_refs=[])),
            ("argv-mismatch", lambda c, d: d["stage"].update(argv=["other"])),
            ("unbound-result", lambda c, d: d["completion"].update(refs=[])),
            ("completion-mismatch", lambda c, d: d["completion"].update(observed={})),
            ("wrong-C20", lambda c, d: d["encoder_library"].update(artifact={})),
            (
                "wrong-closure",
                lambda c, d: d["encoder_closure"].update(upstream_commit="d" * 40),
            ),
            ("GPU-control", lambda c, d: d["execution"].update(GPU=1)),
            ("missing-model-custody", lambda c, d: c.update(model_identity=None)),
            (
                "model-lifetime-drift",
                lambda c, d: c.update(model_identity=[1, 9, 33188, 28685398, 3, 4]),
            ),
        ]
        for name, mutate in cases:
            with self.subTest(case=name):
                cfg, data, bound, identity = fixture()
                mutate(cfg, data)
                with (
                    patch.object(owner, "bound_file_bytes", bound),
                    patch.object(owner, "file_identity", return_value=tuple(identity)),
                    self.assertRaises(ValueError),
                ):
                    owner.cpu_policy_teacher_boundary(cfg)


class OldJointInputExclusionMetadata(unittest.TestCase):
    """New NN0 definitions: admission only, fake readers, no target execution here."""

    @staticmethod
    def fixture(output):
        def ref(name, size=1):
            return dict(
                path="/synthetic-old-joint/" + name, sha256="a" * 64, bytes=size, mode="0644"
            )

        config = dict(
            input_classes=ref("new-input"),
            runtime_boundary={"result": ref("runtime")},
            model=ref("model"),
            model_identity=[1, 2, 33188, 1, 3, 4],
            core_library=ref("core"),
            c20_library=ref("c20"),
            output=str(output),
            batch_rows=2,
            device="cpu",
            cpu_threads=1,
            temperature=1,
            prior_actual_rows=0,
            inclusive_row_limit=4,
        )
        previous = copy.deepcopy(config)
        previous.update(input_classes=ref("old-input"), output="/synthetic-old-joint/old")
        source = dict(
            input_classes=previous["input_classes"],
            teacher_values=ref("teacher-values.json"),
            configuration=ref("old-config"),
        )
        config["excluded_joint_source"] = source
        policy = dict(
            action_order="absolute-core-action-id209",
            value_perspective="side-to-move",
            input_coordinates="canonical-public-STM0-native-C20",
            orientation_targets="independent same-forward actual input orientations",
            temperature=1,
            probabilities=ref("policy", 1672),
            probabilities_identity=[1, 3, 33188, 1672, 3, 4],
            legal_mask=ref("mask", 418),
            legal_mask_identity=[1, 4, 33188, 418, 3, 4],
        )
        bank = dict(
            schema="quoridor-public-static-teacher-values-v1",
            status="COMPLETE",
            input_classes=previous["input_classes"],
            teachers={
                "C": dict(
                    model=config["model"],
                    policy=policy,
                    head=dict(
                        device="cpu",
                        fp32=True,
                        autocast=False,
                        tf32=False,
                        value="raw-local-stm-single-network-post-tanh",
                        failed_attempted_rows=0,
                        constructor_model_calls=0,
                        logical_rows_attempted=2,
                        finite_rows_returned=2,
                    ),
                )
            },
            runtime_boundary=config["runtime_boundary"],
            core_library=config["core_library"],
            c20_library=config["c20_library"],
            actual_orientation_rows=2,
            prior_actual_rows=0,
            inclusive_attempted_rows=2,
        )
        keys = {"old-input": (b"a" * 28, b"b" * 28), "new-input": (b"c" * 28, b"d" * 28)}
        return config, previous, bank, keys

    def admission(self, config, previous, bank, keys):
        from contextlib import contextmanager

        @contextmanager
        def pairs(reference):
            yield {}, keys[reference["path"].rsplit("/", 1)[-1]]

        def bound(reference, cap):
            name = reference["path"].rsplit("/", 1)[-1]
            if name in ("core", "c20"):
                return b""
            data = {"old-config": previous, "teacher-values.json": bank}
            raw = json.dumps(data[name]).encode()
            self.assertLessEqual(len(raw), cap)
            return raw

        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(patch.object(owner, "input_pairs", pairs))
        stack.enter_context(patch.object(owner, "bound_file_bytes", bound))
        stack.enter_context(
            patch.object(owner, "oriented_keys", lambda pairs, capacity: iter([((), (), pairs)]))
        )
        stack.enter_context(
            patch.object(
                owner, "cpu_policy_teacher_boundary", return_value=config["model_identity"]
            )
        )
        return stack

    def test_old_joint_refusals_precede_encoder_and_head_nn0(self):
        import tempfile
        from pathlib import Path

        cases = (
            ("missing-authority", lambda c, p, b, k: c.update(excluded_joint_source=None)),
            ("missing-source", lambda c, p, b, k: c["excluded_joint_source"].pop("configuration")),
            ("missing-bank-provenance", lambda c, p, b, k: b.pop("runtime_boundary")),
            ("failed-bank", lambda c, p, b, k: b.update(status="INCOMPLETE")),
            ("source-mismatch", lambda c, p, b, k: p.update(model={})),
            ("unknown-head", lambda c, p, b, k: b["teachers"]["C"].pop("head")),
            (
                "failed-head",
                lambda c, p, b, k: b["teachers"]["C"]["head"].update(failed_attempted_rows=1),
            ),
            (
                "wrong-temperature",
                lambda c, p, b, k: b["teachers"]["C"]["policy"].update(temperature=2),
            ),
            (
                "missing-policy-provenance",
                lambda c, p, b, k: b["teachers"]["C"]["policy"].update(probabilities=None),
            ),
            (
                "policy-size-identity-mismatch",
                lambda c, p, b, k: b["teachers"]["C"]["policy"]["probabilities"].update(bytes=1),
            ),
            (
                "mask-size-identity-mismatch",
                lambda c, p, b, k: b["teachers"]["C"]["policy"]["legal_mask"].update(bytes=1),
            ),
            (
                "policy-mode-identity-mismatch",
                lambda c, p, b, k: b["teachers"]["C"]["policy"]["probabilities"].update(
                    mode="0600"
                ),
            ),
            (
                "identity-size-type",
                lambda c, p, b, k: b["teachers"]["C"]["policy"].update(
                    probabilities_identity=[1, 3, 33188, "1672", 3, 4]
                ),
            ),
            (
                "identity-bool-primitive",
                lambda c, p, b, k: b["teachers"]["C"]["policy"].update(
                    probabilities_identity=[True, 3, 33188, 1672, 3, 4]
                ),
            ),
            (
                "identity-nonregular-mode",
                lambda c, p, b, k: b["teachers"]["C"]["policy"].update(
                    probabilities_identity=[1, 3, 16877, 1672, 3, 4]
                ),
            ),
            (
                "FileRef-bool-bytes",
                lambda c, p, b, k: b["teachers"]["C"]["policy"]["probabilities"].update(bytes=True),
            ),
            (
                "FileRef-invalid-sha",
                lambda c, p, b, k: b["teachers"]["C"]["policy"]["probabilities"].update(
                    sha256="g" * 64
                ),
            ),
            (
                "FileRef-relative-path",
                lambda c, p, b, k: b["teachers"]["C"]["policy"]["probabilities"].update(
                    path="relative-policy.bin"
                ),
            ),
            ("bool-original-prior", lambda c, p, b, k: p.update(prior_actual_rows=False)),
            ("partial-census", lambda c, p, b, k: b.update(actual_orientation_rows=1)),
            ("exact-overlap", lambda c, p, b, k: k.update({"new-input": (b"a" * 28,)})),
            ("trueLR-port-overlap", lambda c, p, b, k: k.update({"new-input": (b"b" * 28,)})),
        )
        for name, mutate in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                config, previous, bank, keys = self.fixture(Path(directory) / "output")
                mutate(config, previous, bank, keys)
                with (
                    self.admission(config, previous, bank, keys),
                    patch.object(
                        owner, "StaticInputs", side_effect=AssertionError("encoder entered")
                    ) as encoder,
                    patch.object(
                        owner, "StaticHead", side_effect=AssertionError("head entered")
                    ) as head,
                    self.assertRaises((ValueError, KeyError)),
                ):
                    owner.label_policy_values(config)
                encoder.assert_not_called()
                head.assert_not_called()
                failure = json.loads((Path(config["output"]) / "failure.json").read_text())
                self.assertIsNone(failure["head"])
                self.assertTrue((Path(config["output"]) / "INCOMPLETE").exists())
                self.assertFalse((Path(config["output"]) / "cache.json").exists())

    def test_no_overlap_reaches_existing_encoder_path_nn0(self):
        import tempfile
        from pathlib import Path

        class ExistingEncoderPath(Exception):
            pass

        with tempfile.TemporaryDirectory() as directory:
            config, previous, bank, keys = self.fixture(Path(directory) / "output")
            with (
                self.admission(config, previous, bank, keys),
                patch.object(owner, "StaticInputs", side_effect=ExistingEncoderPath) as encoder,
                patch.object(owner, "StaticHead") as head,
                self.assertRaises(ExistingEncoderPath),
            ):
                owner.label_policy_values(config)
            encoder.assert_called_once()
            head.assert_not_called()
            receipt = json.loads((Path(config["output"]) / "old-input-exclusion.json").read_text())
            self.assertEqual(receipt["old_actual_orientation_rows"], 2)
            self.assertEqual(receipt["current_actual_orientation_rows"], 2)
            self.assertEqual(receipt["overlapping_actual_input_keys"], 0)
            self.assertEqual(receipt["labels_read_or_copied"], 0)
