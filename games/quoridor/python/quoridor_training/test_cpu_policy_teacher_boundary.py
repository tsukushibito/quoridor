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
