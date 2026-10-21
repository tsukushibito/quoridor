"""Finite fresh-initial/score math qualification; no optimizer, fit or old model."""

import hashlib
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from .common import resolve_config
from .scaled_model import validate_statistics
from .distance_steps import recipe, build_model, nonterminal_bound
from .cache import load
from .sampling import ReflectionBatches, EpochSampler
from .supply import PackedSupply


class InitialStepMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        print(
            "FRAMEWORK",
            torch.__version__,
            "threads",
            torch.get_num_threads(),
            "interop",
            torch.get_num_interop_threads(),
            "CPU",
            sorted(os.sched_getaffinity(0)),
            flush=True,
        )

    def config(self, name):
        import json

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipe.json"
            path.write_text(json.dumps(recipe(name)))
            return resolve_config(path)

    def test_shared_zero_head_fresh_parameters_and_four_outputs(self):
        identities = []
        models = []
        stats = validate_statistics({"mu_f32": [0.1, 0.1], "sigma_f32": [0.05, 0.05]})
        x = torch.zeros((1, 2, 312), dtype=torch.float32)
        d = torch.tensor([[0.1, 0.2]], dtype=torch.float32)
        side = torch.ones(1, dtype=torch.long)
        integer = torch.tensor([[8.0, 16.0]])
        for name in "ABCD":
            cfg = self.config(name)
            torch.manual_seed(19080311)
            model = build_model(cfg["model"], stats)
            identities.append(
                hashlib.sha256(
                    b"".join(
                        v.detach().numpy().astype("<f4").tobytes()
                        for v in model.state_dict().values()
                    )
                ).hexdigest()
            )
            models.append(model)
            self.assertEqual(torch.count_nonzero(model.out.weight).item(), 0)
            self.assertEqual(torch.count_nonzero(model.out.bias).item(), 0)
            print("INITIAL_FORWARD_ATTEMPT", name, flush=True)
            with torch.inference_mode():
                value = model(x, d, side, integer)
            print("INITIAL_FORWARD_RETURN", name, float(value.item()), flush=True)
            expected = (
                80 * torch.tanh(torch.tensor(8.0) / 80)
                if name in "AB"
                else (torch.tensor(8.0) if name == "C" else torch.tensor(0.0))
            )
            self.assertEqual(value.item(), expected.item())
            print("INITIAL_FORWARD_VALIDATED", name, flush=True)
            bound = nonterminal_bound(
                [
                    v.detach().numpy()
                    for v in [
                        model.ft.weight,
                        model.ft.bias,
                        model.h.weight,
                        model.h.bias,
                        model.out.weight,
                        model.out.bias,
                    ]
                ],
                stats,
                cfg["model"]["distance_bypass"],
            )
            self.assertGreaterEqual(bound, abs(value.item()))
        self.assertEqual(len(set(identities)), 1)
        print("SHARED_ZERO_HEAD_PARAMETER_SHA256", identities[0], flush=True)
        self.assertEqual(
            set(models[0].state_dict()),
            {"ft.weight", "ft.bias", "h.weight", "h.bias", "out.weight", "out.bias"},
        )

    def test_F_gradient_and_loss_normalizer_no_optimizer(self):
        score = torch.tensor(40.0, requires_grad=True)
        value = 80 * torch.tanh(score / 80)
        loss = (value - 80).square() / 6400
        loss.backward()
        expected = (
            2
            * (value.detach().item() - 80)
            / 6400
            * (1 - torch.tanh(score.detach() / 80).item() ** 2)
        )
        self.assertAlmostEqual(score.grad.item(), expected, places=8)
        self.assertTrue(torch.isfinite(score.grad))

    def test_packed_two_workers_keep_exact_integer_bypass_and_scaled_outcome(self):
        fixture = os.environ.get("QUORIDOR_TERMINAL_CACHE_FIXTURE")
        if not fixture:
            self.skipTest("only new owned Rust fixture")
        c = load(Path(fixture) / "cache")
        r = ReflectionBatches(c, 0.5, 19080314)
        sampler = EpochSampler([0, 1], 1, 19080311)
        supply = PackedSupply(
            r, 1, "cpu", np.ones(2, dtype=np.float32), 1, workers=2, target_scale=80
        )
        try:
            for _ in range(2):
                index = sampler.next_batch()
                inputs, target, weights = supply.batch(index, training=True, sampler=sampler)
                self.assertEqual(len(inputs), 4)
                np.testing.assert_array_equal(inputs[3].numpy(), c.integer_distances[index])
                np.testing.assert_array_equal(target.numpy(), 80 * c.labels[index, 1])
                np.testing.assert_array_equal(weights.numpy(), [1])
        finally:
            supply.close()
        self.assertEqual(supply.queue.consumed_rows, 2)


if __name__ == "__main__":
    unittest.main()
