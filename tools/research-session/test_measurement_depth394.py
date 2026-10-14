"""One new optional-depth metadata boundary; no native/model/Search execution."""

from test_measurement import MeasurementTests as _MeasurementFixture
from test_measurement import lc


class MeasurementDepthSwitch394(_MeasurementFixture):
    def test_measurement394_optional_completed_depth_switch_is_boolean_and_opaque(self):
        rows = self.configure(["depth-observation"])
        for enabled in (None, False, True):
            with self.subTest(enabled=enabled):
                if enabled is None:
                    rows[0].pop("observe_completed_depths", None)
                else:
                    rows[0]["observe_completed_depths"] = enabled
                self.experiment["schedule"] = self.metadata("schedule.json", rows)
                _, admitted = lc.measurement_config(self.experiment)
                self.assertEqual(admitted, rows)
                self.assertEqual(
                    admitted[0].get("observe_completed_depths", False), bool(enabled)
                )
                self.assertNotIn("completed_depth_observations", admitted[0])
        for invalid in (None, 0, 1, "true", []):
            rows[0]["observe_completed_depths"] = invalid
            self.experiment["schedule"] = self.metadata("schedule.json", rows)
            with (
                self.subTest(invalid=invalid),
                self.assertRaisesRegex(lc.Refused, "request switches"),
            ):
                lc.measurement_config(self.experiment)
        rows[0]["observe_completed_depths"] = True
        rows[0]["foreign_switch"] = True
        self.experiment["schedule"] = self.metadata("schedule.json", rows)
        with self.assertRaisesRegex(lc.Refused, "request type/range/identity"):
            lc.measurement_config(self.experiment)
