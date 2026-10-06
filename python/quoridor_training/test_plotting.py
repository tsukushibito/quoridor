"""One bounded synthetic XML suite; no labels, models, Torch or forward."""

from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from .plotting import render_learning_curves


class RenderingContracts(unittest.TestCase):
    def fixture(self):
        points = []
        for step, train, validation, scope in [
            (0, 0.615, 0.661, "full_train"),
            (1000, 0.280, 0.586, "fixed_diagnostic_subset"),
            (4000, 0.005, 0.748, "full_train"),
        ]:
            points.append(
                {
                    "step": step,
                    "training_seen": step * 128,
                    "row_epoch": step * 128 / 14803,
                    "completed_epochs": None,
                    "train_scope": scope,
                    "train": {
                        "target_mse": train + 0.1,
                        "target_game_equal_mse": train,
                        "distance_ref": scope,
                        "constant_mse": 1.01,
                        "constant_game_equal_mse": 1.0,
                    },
                    "validation": {
                        "target_mse": validation + 0.03,
                        "target_game_equal_mse": validation,
                        "distance_ref": "V",
                        "constant_mse": 1.02,
                        "constant_game_equal_mse": 1.01,
                        "z_sign_accuracy": None,
                    },
                }
            )
        refs = {
            scope: {"distance": {"target_mse": 0.7, "target_game_equal_mse": 0.66}}
            for scope in ["full_train", "fixed_diagnostic_subset", "V"]
        }
        return points, refs

    def render(self, points, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "curve.svg"
            result = render_learning_curves(points, p, **kwargs)
            text = p.read_text()
            xml = ET.fromstring(text)
        return xml, text, result

    @staticmethod
    def elements(xml, cls):
        return [node for node in xml.iter() if cls in node.attrib.get("class", "").split()]

    def test_axes_scopes_markers_selection_and_references(self):
        points, refs = self.fixture()
        xml, text, result = self.render(
            points, selected_step=1000, references=refs, sampling="game"
        )
        markers = self.elements(xml, "measured-point")
        self.assertEqual(len(markers), 12)
        self.assertEqual(result["measured_markers"], 12)
        self.assertEqual(len(self.elements(xml, "selected-marker")), 2)
        self.assertEqual({p.attrib["data-step"] for p in markers}, {"0", "1000", "4000"})
        full = [p for p in markers if p.attrib["data-scope"] == "full_train"]
        self.assertEqual({p.attrib["data-step"] for p in full}, {"0", "4000"})
        self.assertFalse(
            any(
                p.attrib["data-scope"] == "full_train" for p in self.elements(xml, "recorded-guide")
            )
        )
        self.assertEqual(
            {p.attrib["data-kind"] for p in self.elements(xml, "baseline")},
            {"distance", "constant"},
        )
        self.assertTrue(self.elements(xml, "x-tick"))
        self.assertTrue(self.elements(xml, "y-tick"))
        self.assertTrue(self.elements(xml, "exposure-tick"))
        self.assertIn("Group / family-equal MSE", text)
        self.assertIn("Row MSE", text)
        self.assertIn("Equivalent random row-passes", text)
        self.assertIn("seen 128000", text)
        self.assertIn("missing eligible z is not zero", text)

    def test_empty_has_no_measured_or_selected_point(self):
        xml, text, result = self.render([], selected_step=0)
        self.assertEqual(result["measured_markers"], 0)
        self.assertFalse(self.elements(xml, "measured-point"))
        self.assertFalse(self.elements(xml, "selected-marker"))
        self.assertEqual(len(self.elements(xml, "empty-state")), 2)
        self.assertIn("No completed measurements", text)

    def test_one_point_no_fake_guide_or_inferred_selection(self):
        points, refs = self.fixture()
        xml, _, result = self.render(points[:1], references=refs)
        self.assertEqual(result["measured_markers"], 4)
        self.assertFalse(self.elements(xml, "recorded-guide"))
        self.assertFalse(self.elements(xml, "selected-marker"))

    def test_actual_epochs_and_diagnostic_validation_are_explicit(self):
        points, _ = self.fixture()
        for p in points:
            p["completed_epochs"] = int(p["row_epoch"])
            p["partial_epoch_fraction"] = p["row_epoch"] % 1
            p["scope"] = "fixed_target_blind_subset"
            p["used_for_selection"] = False
        xml, text, _ = self.render(points, sampling="epoch", selected_step=1000)
        self.assertIn("Actual epochs (completed + partial)", text)
        self.assertTrue(
            any(
                p.attrib["data-scope"] == "validation_diagnostic_subset"
                for p in self.elements(xml, "measured-point")
            )
        )
        self.assertFalse(self.elements(xml, "selected-marker"))

    def test_missing_numeric_measurements_not_zero_and_title_escaped(self):
        points, _ = self.fixture()
        points[0]["train"]["target_mse"] = None
        points[0]["validation"]["target_game_equal_mse"] = float("nan")
        xml, text, result = self.render(points[:1], title="A < B & C")
        self.assertEqual(result["measured_markers"], 2)
        self.assertIn("A &lt; B &amp; C", text)
        self.assertEqual(len(self.elements(xml, "measured-point")), 2)


if __name__ == "__main__":
    unittest.main()
