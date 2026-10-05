"""NN0 reconstruction of the fixed-root profile's saved arithmetic."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
old = ROOT.parent / "frame21-search-efficiency" / "candidate-r1" / "stdout.log"
previous = [json.loads(line) for line in old.read_text().splitlines()]
rows = [json.loads(line) for line in (ROOT / "profile-r1/stdout.log").read_text().splitlines()]
result = json.loads((ROOT / "result.json").read_text())
roots = rows[:-1]
assert len(roots) == 4
for row in roots:
    reference = next(
        item
        for item in previous
        if item["kind"] == "mcts" and item["name"] == row["name"] and item["sample"] == 0
    )
    fixture = next(
        item for item in previous if item["kind"] == "fixture" and item["name"] == row["name"]
    )
    for key in (
        "action",
        "root_visits",
        "root_mean_bits",
        "edge_visits",
        "prior_mass",
        "nodes",
        "max_depth",
        "nn_calls",
        "terminal_no_nn",
        "edges_hash",
    ):
        assert row[key] == reference[key], (row["name"], key)
    for key in ("prefix", "key", "feature_sha", "legal"):
        assert row[key] == fixture[key], (row["name"], key)
    assert (
        sum(
            row[key]
            for key in (
                "setup_ns",
                "advance_ns",
                "infer_ns",
                "supply_ns",
                "unattributed_ns",
            )
        )
        == row["whole_root_ns"]
    )
for key, total in result["sum_ns"].items():
    assert total == sum(row[key] for row in roots)
assert rows[-1]["actual_native_nn"] == sum(row["nn_calls"] for row in roots) == 256
assert rows[-1]["allocated_tree_nodes"] == sum(row["nodes"] for row in roots) == 30856
print(
    json.dumps(
        {
            "task": "frame21-mcts-cost-271-v1",
            "schema": "saved-arithmetic-v1",
            "status": "PASS",
            "model_import": False,
            "forward": 0,
        }
    )
)
