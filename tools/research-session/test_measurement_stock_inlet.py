"""The new normal LC Boolean inlet only; no native or model execution."""

import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/dev/research-lifecycle.py"
SPEC = importlib.util.spec_from_file_location("stock_request_inlet", SOURCE)
lc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lc
SPEC.loader.exec_module(lc)


class StockRequestInlet(unittest.TestCase):
    def test_explicit_stock_boolean_reaches_native_and_rejects_wrong_types(self):
        config = dict(
            roots=[dict(input=0, pointer="/0", field="prefix", label="new-metadata-unit")],
            profile="control",
            tt_entries=1048576,
            use_tt=True,
            use_pvs=True,
            lmr=True,
            lmr_method="depth_rank",
            zero_stock_safe_race=True,
            zero_stock_safe_race_method="path_tail_future",
            seed=32462018,
            namespace=dict(evaluator="unit", rules="standard", selectivity="unit"),
            output_bytes=3145728,
            record_bytes=24576,
        )
        request = dict(id="new-unit", session="one", root=0, depth=8, node_cap=4000000)
        experiment = dict(
            config="unit-config", schedule="unit-requests", rules="standard", inputs=[{}]
        )
        for observed in (False, True):
            requests = [{**request, "observe_stock": observed}]
            documents = {"unit-config": config, "unit-requests": requests}
            with patch.object(lc, "document", side_effect=documents.__getitem__):
                actual_config, actual_requests = lc.measurement_config(experiment)
            self.assertIs(actual_config, config)
            self.assertIs(actual_requests, requests)
            self.assertIs(actual_requests[0]["observe_stock"], observed)
        for wrong in (None, 0, 1, "true", [], {}):
            documents = {
                "unit-config": config,
                "unit-requests": [{**request, "observe_stock": wrong}],
            }
            with (
                patch.object(lc, "document", side_effect=documents.__getitem__),
                self.assertRaises(lc.Refused),
            ):
                lc.measurement_config(experiment)
        # The normal absent-field route remains available; no default observer is injected.
        documents = {"unit-config": config, "unit-requests": [copy.deepcopy(request)]}
        with patch.object(lc, "document", side_effect=documents.__getitem__):
            _, actual = lc.measurement_config(experiment)
        self.assertNotIn("observe_stock", actual[0])
        documents["unit-requests"][0]["observe_stock_unimplemented"] = True
        with (
            patch.object(lc, "document", side_effect=documents.__getitem__),
            self.assertRaises(lc.Refused),
        ):
            lc.measurement_config(experiment)


if __name__ == "__main__":
    unittest.main()
