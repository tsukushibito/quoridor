"""Synthetic output-only subprocess for argv/schema qualification; no native math."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("selfplay")
parser.add_argument("--config", required=True)
parser.add_argument("--registration", required=True)
args = parser.parse_args()
native = json.loads(Path(args.config).read_text())
manifest = json.loads(Path(args.registration).read_text())
rows = [r for r in manifest["families"] if r["native_run_id"] == native["run_id"]]
out = Path(native["output"])
out.mkdir(exist_ok=False)
(out / "result.json").write_text(
    json.dumps(
        {
            "schema": "quoridor-run-v1",
            "run_id": native["run_id"],
            "planned": 48,
            "model_sha": native["inference"]["model_sha"],
            "nn_calls": 0,
            "pump": {"backend_warmup_nn": 0},
        }
    )
    + "\n"
)
(out / "planned.json").write_text(
    json.dumps(
        [
            {
                "game": r["local_id"],
                "family": r["native_family"],
                "opening": r["prefix"],
                "split": "Test",
            }
            for r in rows
        ]
    )
    + "\n"
)
