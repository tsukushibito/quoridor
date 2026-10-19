"""Pure metadata mode boundary; never opens input/model or runs Search."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
loader = importlib.util.spec_from_file_location(
    "neighbour_lifecycle", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class NeighbourHistoryMetadataTests(unittest.TestCase):
    def test_neighbour_mode_scope_defaults_removed_name_and_normal_composition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            requests = root / "requests.json"
            requests.write_text(
                json.dumps(
                    [
                        dict(
                            id="unit",
                            session="unit-session",
                            root=0,
                            depth=1,
                            node_cap=16,
                        )
                    ]
                )
            )
            config_path = root / "config.json"
            config = dict(
                roots=[dict(input=0, pointer="", field="prefix", label="not-opened")],
                profile="control",
                tt_entries=32,
                use_tt=True,
                use_pvs=True,
                namespace=dict(
                    evaluator="fixture-no-model", rules="fixture", selectivity="PVS"
                ),
                output_bytes=65536,
                record_bytes=4096,
            )

            def check(value):
                config_path.write_text(json.dumps(value))
                return lc.measurement_config(
                    dict(
                        config=lc.artifact_ref(config_path),
                        schedule=lc.artifact_ref(requests),
                        rules="fixture",
                        inputs=[dict(path="/synthetic-never-opened")],
                    )
                )

            for profile in ["control", "cheap", "coverage"]:
                for explicit in [
                    {},
                    {"history_tie_break": None},
                    {"history_tie_break": "off"},
                ]:
                    value = {**config, "profile": profile, **explicit}
                    actual, schedule = check(value)
                    self.assertEqual(actual, value)
                    self.assertEqual(len(schedule), 1)
            selected = {**config, "history_tie_break": "neighbour_contact"}
            self.assertEqual(check(selected)[0], selected)
            for profile in ["cheap", "coverage"]:
                with self.assertRaisesRegex(
                    lc.Refused, "measurement history tie break"
                ):
                    check({**selected, "profile": profile})
            for unknown in ["local_goal_edge", "unknown", True, 0, "OFF"]:
                with self.assertRaisesRegex(
                    lc.Refused, "measurement history tie break"
                ):
                    check({**config, "history_tie_break": unknown})
            common = dict(
                evaluators=["nnue"],
                profiles=["control"],
                history_tie_breaks=["off", "neighbour_contact"],
            )
            variants = lc.comparison_conditions(common)
            self.assertEqual(
                [row["history_tie_break"] for row in variants],
                ["off", "neighbour_contact"],
            )
            self.assertTrue(
                all(row["lmr"] and row["zero_stock_safe_race"] for row in variants)
            )
            self.assertTrue(
                all(
                    row["lmr_method"] == "depth_rank"
                    and row["zero_stock_safe_race_method"] == "path_tail"
                    for row in variants
                )
            )


if __name__ == "__main__":
    unittest.main()
