"""NEW model-free shared-seed boundaries; Root execution only."""

import ast
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

NEW_SEED = 2026102403064


def load_matches():
    package = types.ModuleType("seed_boundary")
    package.__path__ = []
    engines = types.ModuleType("seed_boundary.engines")
    for name in (
        "io_deadline",
        "validate_native_search",
        "validate_full_search",
        "validate_external_search",
    ):
        setattr(engines, name, lambda *a, **k: None)
    protocol = types.ModuleType("seed_boundary.protocol")
    protocol.EngineError = type("FakeEngineError", (Exception,), {})
    source = Path(os.environ["OTHELLO_MATCHES_SOURCE"])
    spec = importlib.util.spec_from_file_location("seed_boundary.matches", source)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            "seed_boundary": package,
            "seed_boundary.engines": engines,
            "seed_boundary.protocol": protocol,
        },
    ):
        spec.loader.exec_module(module)
    return module


class SharedBootstrapSeedBoundary(unittest.TestCase):
    def test_explicit_new_seed_one_table_two_consumers(self):
        owner = load_matches()
        calls = {"seed": [], "generator": 0, "consumers": [], "quantiles": []}
        indices = types.SimpleNamespace(shape=(10000, 16), dtype=types.SimpleNamespace(str="<i8"))
        indices.astype = lambda dtype, copy: indices
        indices.tobytes = lambda order: b"fake-table-not-random"

        def pcg(seed):
            calls["seed"].append(seed)
            return object()

        def generator(bitgen):
            calls["generator"] += 1

            def integers(low, high, *, size, dtype):
                self.assertEqual((low, high, size, dtype), (0, 16, (10000, 16), "i64"))
                return indices

            return types.SimpleNamespace(integers=integers)

        class Values:
            def __getitem__(self, table):
                calls["consumers"].append(table)
                return types.SimpleNamespace(mean=lambda axis: "fake-resampled-means")

        def quantile(samples, tails, *, method):
            calls["quantiles"].append((samples, tails, method))
            return 0.25, 0.75

        numpy = types.SimpleNamespace(
            __version__="fake-no-numpy-runtime",
            int64="i64",
            random=types.SimpleNamespace(PCG64=pcg, Generator=generator),
            asarray=lambda values, dtype: Values(),
            quantile=quantile,
        )
        families = [f"declared-family-{i:02}" for i in range(16)]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"numpy": numpy}):
            shared = owner.family_bootstrap_table(
                families, Path(tmp) / "fake-indices", seed=NEW_SEED
            )
            self.assertEqual(shared["metadata"]["seed"], NEW_SEED)
            for means in ([0.0] * 16, [1.0] * 16):
                self.assertEqual(
                    owner._shared_family_interval(means, families, shared), (0.25, 0.75)
                )
        self.assertEqual(calls["seed"], [NEW_SEED])
        self.assertEqual(calls["generator"], 1)
        self.assertEqual(calls["consumers"], [indices, indices])
        self.assertEqual(
            calls["quantiles"],
            [("fake-resampled-means", [0.025, 0.975], "linear")] * 2,
        )

    def test_seed_rejected_before_import_and_caller_forwards_config(self):
        owner = load_matches()
        with patch.dict(sys.modules, {"numpy": None}):
            for seed in (None, True, -1, 1.5, "2026102403064"):
                with self.subTest(seed=seed), self.assertRaises(ValueError):
                    owner.family_bootstrap_table(
                        [f"f{i}" for i in range(16)], Path("UNWRITTEN"), seed=seed
                    )
        tree = ast.parse(Path(os.environ["OTHELLO_ARENA_SOURCE"]).read_text())
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "family_bootstrap_table"
        ]
        self.assertEqual(len(calls), 1)
        value = next(keyword.value for keyword in calls[0].keywords if keyword.arg == "seed")
        self.assertEqual(
            ast.dump(value, include_attributes=False),
            ast.dump(
                ast.parse('config["statisticsContract"]["seed"]', mode="eval").body,
                include_attributes=False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
