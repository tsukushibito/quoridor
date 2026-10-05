"""Registered native generation wrapper, source/task/output binding only."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
cfg = json.loads(Path(parser.parse_args().config).read_text())
assert not Path(cfg["output"]).exists()
assert (
    hashlib.sha256(Path(cfg["native_config"]).read_bytes()).hexdigest() == cfg["native_config_SHA"]
)
began = time.monotonic()
completed = subprocess.run(cfg["argv"], check=False)
report_path = Path(cfg["native_output"]) / "result.json"
report = json.loads(report_path.read_text()) if report_path.exists() else None
if report is not None:
    assert report["schema"] == "quoridor-run-v1" and report["run_id"] == cfg["native_run_id"]
    assert report["planned"] == 48 and report["model_sha"] == cfg["model_SHA"]
    assert report["nn_calls"] + report["pump"]["backend_warmup_nn"] <= cfg["physical_NN_upper"]
Path(cfg["output"]).write_text(
    json.dumps(
        {
            "task": cfg["task"],
            "schema": "resident-teacher-pipeline-v1",
            "native_exit": completed.returncode,
            "native_report_path": str(report_path),
            "native_report_SHA": hashlib.sha256(report_path.read_bytes()).hexdigest()
            if report
            else None,
            "native_config_SHA": cfg["native_config_SHA"],
            "family_map_SHA": cfg["family_map_SHA"],
            "wrapper_native_wall_s": time.monotonic() - began,
            "physical_NN": report["nn_calls"] + report["pump"]["backend_warmup_nn"]
            if report
            else None,
            "status": "COMPLETED" if completed.returncode == 0 else "PARTIAL_OR_FAILED",
        },
        indent=2,
    )
    + "\n"
)
raise SystemExit(completed.returncode)
