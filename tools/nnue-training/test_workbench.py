"""Software tests with synthetic rows; never run research teachers through training."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from common import EarlyStopping, load_data, measurements, resolve_config


def fixture():
    return [{"id": str(i), "group": f"game{i // 2}", "split": "train" if i < 4 else "validation", "cohort": "synthetic", "ids": [[i, 81+i, 290, 301], [80-i, 161-i, 290, 301]], "distance": [.1+i*.01, .2], "side": 1 if i % 2 else 2, "rootmean": .2 if i % 2 else -.2, "z": 1 if i % 2 else -1} for i in range(6)]


class WorkbenchTests(unittest.TestCase):
    def test_config_overrides_and_invalid_values(self):
        cfg = resolve_config(overrides=["optimizer.lr=0.00025", "model.hidden_width=16", 'training.target="z"'])
        self.assertEqual(cfg["optimizer"]["lr"], .00025)
        self.assertEqual(cfg["model"]["hidden_width"], 16)
        self.assertEqual(cfg["training"]["target"], "z")
        for arg in ["optimizer.lr=NaN", "training.steps=true", "training.seed=-1", "model.dropout=1", 'evaluation.monitor="invalid"', "unknown.x=1"]:
            with self.subTest(arg=arg), self.assertRaises(ValueError):
                resolve_config(overrides=[arg])

    def test_split_checks_and_missing_z(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.json"
            rows = fixture()
            rows[0]["z"] = None
            p.write_text(json.dumps(rows))
            valid, info = load_data(p)
            self.assertEqual(info["groups"], {"train": 2, "validation": 1})
            self.assertIsNone(valid[0]["z"])
            rows[4]["state_key"] = rows[0]["state_key"] = "shared"
            p.write_text(json.dumps(rows))
            with self.assertRaises(ValueError):
                load_data(p)
            self.assertEqual(load_data(p, "report")[1]["cross_split_keys"]["state_key"], 1)
            rows[4]["exposure_group"] = rows[0]["exposure_group"] = "same-family"
            p.write_text(json.dumps(rows))
            with self.assertRaises(ValueError):
                load_data(p, "report")

    def test_measurements_do_not_treat_missing_outcome_as_draw(self):
        rows = fixture()[:3]
        for r in rows:
            r["rootmean"] = 0
        rows[0]["z"] = None
        m = measurements(rows, [0, 0, 1], "rootmean", 0)
        self.assertAlmostEqual(m["target_mse"], 1/3)
        self.assertAlmostEqual(m["target_game_equal_mse"], .5)
        self.assertEqual(m["z_rows"], 2)
        self.assertAlmostEqual(m["z_mse"], 2.5)
        rows[1]["z"] = 0
        self.assertEqual(measurements(rows, [0, 0, 1], "rootmean", 0)["z_sign_rows"], 1)

    def test_early_stopping_requires_meaningful_improvement(self):
        stopper = EarlyStopping(2, .01)
        self.assertEqual(stopper.observe(1), (True, False))
        self.assertEqual(stopper.observe(.995), (False, False))
        self.assertEqual(stopper.observe(.99), (False, True))
        self.assertEqual(stopper.best, 1)
        self.assertEqual(stopper.observe(.98), (True, False))
        with self.assertRaises(ValueError):
            stopper.observe(float("nan"))

    def test_synthetic_end_to_end(self):
        # Three independent processes: complete run, sample-limit boundary, missing target.
        # Only 6 artificial rows and a 4-wide network are used, not saved research data.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            p = tmp / "synthetic.json"
            p.write_text(json.dumps(fixture()))
            root = Path(__file__).resolve().parent
            base = [sys.executable, str(root / "train.py"), "--data", str(p), "--output", str(tmp / "runs"), "--checkpoints", str(tmp / "weights")]
            overrides = ["training.steps=2", "training.batch_size=2", "model.transformer_width=4", "model.hidden_width=4", "evaluation.interval=1", "limits.seconds=30", "limits.samples=30", "optimizer.lr=0.00025"]
            opts = [x for v in overrides for x in ["--set", v]]
            run = subprocess.run(base + ["--run-id", "synthetic"] + opts, capture_output=True, text=True, timeout=40)
            self.assertEqual(run.returncode, 0, run.stderr)
            directory = tmp / "runs" / "synthetic"
            history = [json.loads(x) for x in (directory / "history.jsonl").read_text().splitlines()]
            summary = json.loads((directory / "summary.json").read_text())
            self.assertEqual([x["step"] for x in history], [0, 1, 2])
            self.assertEqual(summary["all_samples"], 22)
            self.assertEqual(summary["status"], "max_steps")
            self.assertEqual(history[-1]["train_samples_seen"], 4)
            self.assertEqual(history[-1]["train_epochs_equivalent"], 1)
            self.assertEqual(history[-1]["lr"], .00025)
            self.assertEqual(history[-1]["monitor"], "target_game_equal_mse")
            scores = [r["validation"][r["monitor"]] for r in history]
            self.assertEqual(summary["best_validation_mse"], min(scores))
            self.assertEqual(summary["best_step"], scores.index(min(scores)))
            self.assertTrue((tmp / "weights" / "synthetic" / "best.pt").is_file())
            self.assertTrue((tmp / "weights" / "synthetic" / "last.pt").is_file())
            again = subprocess.run(base + ["--run-id", "synthetic"] + opts, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("run already exists", again.stderr)
            limited = subprocess.run(base + ["--run-id", "limited"] + opts + ["--set", "limits.samples=7"], capture_output=True, text=True, timeout=40)
            self.assertEqual(limited.returncode, 0, limited.stderr)
            result = json.loads((tmp / "runs" / "limited" / "summary.json").read_text())
            self.assertEqual(result["status"], "sample_limit")
            self.assertEqual(result["step"], 0)
            missing = fixture()
            for row in missing:
                row["z"] = None
            p.write_text(json.dumps(missing))
            bad = subprocess.run(base + ["--run-id", "missing", "--dry-run", "--set", 'training.target="z"'], capture_output=True, text=True, timeout=5)
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse((tmp / "runs" / "missing").exists())
            # The comparison must distinguish validation-selected checkpoints from final holdout.
            compare = subprocess.run([sys.executable, str(root / "compare.py"), "--runs", str(directory), str(tmp / "runs" / "limited"), "--output", str(tmp / "comparison")], capture_output=True, text=True, timeout=5)
            self.assertEqual(compare.returncode, 0, compare.stderr)
            data = json.loads((tmp / "comparison.json").read_text())
            self.assertTrue(data["same_validation_and_target"])
            self.assertTrue(data["validation_selected_not_final_holdout"])
            limited_dataset = tmp / "runs" / "limited" / "dataset.json"
            metadata = json.loads(limited_dataset.read_text())
            metadata["validation_sha256"] = "different"
            limited_dataset.write_text(json.dumps(metadata))
            subprocess.run([sys.executable, str(root / "compare.py"), "--runs", str(directory), str(tmp / "runs" / "limited"), "--output", str(tmp / "comparison")], check=True, capture_output=True, timeout=5)
            self.assertFalse(json.loads((tmp / "comparison.json").read_text())["same_validation_and_target"])
            plot_python = Path("/home/vscode/.cache/inference/envs/quoridor-learning-plots/bin/python")
            if plot_python.is_file():
                result = subprocess.run([str(plot_python), str(root / "plot.py"), "--runs", str(directory), "--output", str(tmp / "curve"), "--axis", "train_samples_seen"], capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((tmp / "curve.png").read_bytes().startswith(b"\x89PNG"))
                self.assertIn("<svg", (tmp / "curve.svg").read_text())


if __name__ == "__main__":
    unittest.main()
