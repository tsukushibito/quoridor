"""Metadata NN0 checks do not import Torch, NumPy or any model module."""

import ast
import os
from pathlib import Path
import tempfile
import unittest


def pure(name):
    source = Path(__file__).with_name("residual_model.py").read_text()
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    scope = {}
    exec(
        compile(
            ast.Module(body=nodes, type_ignores=[]),
            source[:0] + "policy-metadata",
            "exec",
        ),
        scope,
    )
    return scope[name]


class PolicyMetadata(unittest.TestCase):
    def test_core209_stm_reflection_total_nn0(self):
        permutation = pure("policy_permutation")
        self.assertEqual(permutation(1), tuple(range(209)))
        p2 = permutation(2)
        self.assertEqual([p2[a] for a in (0, 80, 81, 144, 145, 208)], [80, 0, 144, 81, 208, 145])
        for side in (1, 2):
            for reflected in (False, True):
                p = permutation(side, reflected=reflected)
                self.assertEqual(sorted(p), list(range(209)))
                self.assertEqual(tuple(p[p[a]] for a in range(209)), tuple(range(209)))
                for low, high in ((0, 81), (81, 145), (145, 209)):
                    self.assertTrue(all(low <= p[a] < high for a in range(low, high)))
        self.assertEqual(permutation(1, reflected=True)[27], 35)
        self.assertEqual(permutation(1, reflected=True)[81], 88)
        self.assertEqual(permutation(1, reflected=True)[145], 152)
        for side in (0, 3, True):
            with self.assertRaises(ValueError):
                permutation(side)

    def test_policy_shared_identity_and_metadata_refusals_nn0(self):
        validate = pure("validate_policy_manifest")
        m = {
            "schema": "quoridor-nnue-policy209-v1",
            "action_order": "absolute-core-action-id209",
            "head_coordinates": "QF1-STM-rotate180",
            "value_perspective": "side-to-move",
            "reflection": "core-action-id209-left-right-v1",
            "evidence": "synthetic_untrained",
            "shared_fingerprint": "a" * 64,
            "hidden_width": 32,
            "weights": "policy.f32",
            "weights_sha256": "b" * 64,
            "weights_bytes": 209 * 33 * 4,
        }
        validate(m, "a" * 64, 32)
        for key, value in (
            ("schema", "policy136"),
            ("shared_fingerprint", "c" * 64),
            ("action_order", "sigma136"),
            ("head_coordinates", "absolute-unlabelled"),
            ("weights", "../weights.f32"),
            ("weights_bytes", 0),
            ("evidence", "uniform"),
            ("hidden_width", True),
        ):
            with self.assertRaises(ValueError, msg=key):
                validate({**m, key: value}, "a" * 64, 32)
        with self.assertRaises(ValueError):
            validate({**m, "unknown": 1}, "a" * 64, 32)


@unittest.skipUnless(
    os.environ.get("QUORIDOR_POLICY_TENSOR_FIXTURE") == "1",
    "Root-only: four NNUE forward rows, inclusive connection cap",
)
class PolicyTensorCorrespondence(unittest.TestCase):
    def test_shared_value_head_save_read_and_loss_four_rows(self):
        import torch
        from .residual_model import (
            DistanceResidualModel,
            load_policy_head,
            policy_value_loss,
        )
        from .train import export_policy_head

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.manual_seed(0)  # synthetic software fixture only

        cfg = {"transformer_width": 2, "hidden_width": 2, "dropout": 0.0}
        stats = {"mu_f32": [0.1, 0.2], "sigma_f32": [0.2, 0.3]}
        model = DistanceResidualModel(cfg, stats, a=0, b=0)
        with torch.no_grad():
            model.h.bias.fill_(0.25)
            model.out.weight.fill_(0.125)
            model.out.bias.fill_(0.375)
        value_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        x = torch.zeros((1, 2, 312), dtype=torch.float32)
        d = torch.tensor([[0.1, 0.2]], dtype=torch.float32)
        side = torch.tensor([2])
        before = model(x, d, side)  # row1
        model.enable_policy_head(evidence="synthetic_untrained")
        value, logits = model.forward_policy_value(x, d, side)  # row2
        self.assertTrue(torch.equal(before, value))
        self.assertTrue(torch.equal(before, model(x, d, side)))  # row3
        for key, tensor in value_state.items():
            self.assertTrue(torch.equal(tensor, model.state_dict()[key]))
        mask = torch.zeros((1, 209), dtype=torch.bool)
        mask[0, [67, 85, 145]] = True
        target = torch.zeros_like(logits)
        target[0, 67] = 1
        loss, terms = policy_value_loss(value, logits, torch.zeros_like(value), target, mask)
        loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertEqual(set(terms), {"outcome_mse", "policy_cross_entropy"})
        self.assertTrue(torch.isfinite(model.policy.weight.grad).all())
        with tempfile.TemporaryDirectory() as directory:
            # Explicitly synthetic metadata fixture; never an actual native identity.
            manifest = export_policy_head(
                model, shared_fingerprint="a" * 64, path=Path(directory) / "head"
            )
            loaded = DistanceResidualModel(cfg, stats, a=0, b=0)
            loaded.load_state_dict(value_state)
            load_policy_head(loaded, manifest, shared_fingerprint="a" * 64)
            restored, restored_logits = loaded.forward_policy_value(x, d, side)  # row4
            self.assertTrue(torch.equal(value, restored))
            self.assertTrue(torch.equal(logits, restored_logits))
            with self.assertRaises(ValueError):
                load_policy_head(
                    DistanceResidualModel(cfg, stats, a=0, b=0),
                    manifest,
                    shared_fingerprint="b" * 64,
                )


if __name__ == "__main__":
    unittest.main()
