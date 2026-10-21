"""Export range evidence from synthetic arrays; no model or native execution."""

from decimal import Decimal, localcontext
import unittest

import numpy as np

from .distance_steps import nonterminal_bound


class ExportLegalEnvelope(unittest.TestCase):
    def arrays(self):
        return [
            np.zeros(shape, dtype=np.float32)
            for shape in [(32, 312), (32,), (32, 70), (32,), (1, 32), (1,)]
        ]

    def statistics(self):
        return {"mu_f32": [0.0, 0.0], "sigma_f32": [1.0, 1.0]}

    def test_zero_head_and_explicit_bypass(self):
        arrays = self.arrays()
        arrays[0].fill(0.125)
        self.assertEqual(nonterminal_bound(arrays, self.statistics(), False), 0.0)
        bound = nonterminal_bound(arrays, self.statistics(), True)
        self.assertGreater(bound, 80.0)
        self.assertEqual(bound, float(np.float32(bound)))

    def test_general_delta_history_dominates_independent_decimal_growth(self):
        arrays = self.arrays()
        arrays[0][0, 0] = 1
        arrays[2][0, 0] = 1
        arrays[4][0, 0] = 1
        with localcontext() as context:
            context.prec = 100
            growth = 1 + Decimal(2) ** -23
            minimum = Decimal(24 + 48 * 200) * growth ** (24 + 48 * 200 + 156 + 80)
            bound = nonterminal_bound(arrays, self.statistics(), False)
            self.assertGreaterEqual(Decimal.from_float(bound), minimum)
        self.assertGreater(bound, 9624)

    def test_dense_scale_and_bias_dominate_exact_norm(self):
        arrays = self.arrays()
        arrays[2][0, 64:66] = [1, -2]
        arrays[3][0] = -3
        arrays[4][0, 0] = -2
        arrays[5][0] = -1
        stats = {"mu_f32": [-0.25, 0.5], "sigma_f32": [0.25, 0.5]}
        # Exact L1 expression over each distance in[0,1], before rounding.
        lower = 1 + 2 * (3 + (1 + 0.25) / 0.25 + 2 * (1 + 0.5) / 0.5)
        self.assertGreater(nonterminal_bound(arrays, stats, False), lower)
        arrays[0][0, 0] = np.nextafter(np.float32(0), np.float32(1))
        arrays[2][0, 0] = 1
        self.assertGreater(nonterminal_bound(arrays, stats, False), lower)

    def test_invalid_parameters_scale_and_unrepresentable_intermediates_refuse(self):
        arrays = self.arrays()
        for value in (np.nan, np.inf, np.finfo(np.float32).max):
            arrays[0][0, 0] = value
            with self.assertRaises(ValueError):
                nonterminal_bound(arrays, self.statistics(), False)
        arrays = self.arrays()
        with self.assertRaises(ValueError):
            nonterminal_bound([a.astype(np.float64) for a in arrays], self.statistics(), False)
        for sigma in (0.0, -1.0, np.inf, np.nan):
            with self.assertRaises(ValueError):
                nonterminal_bound(arrays, {"mu_f32": [0.0, 0.0], "sigma_f32": [sigma, 1]}, False)
        with self.assertRaises(ValueError):
            nonterminal_bound(arrays, self.statistics(), 1)


if __name__ == "__main__":
    unittest.main()
