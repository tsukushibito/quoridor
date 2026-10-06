"""Independent metadata acceptance without importing a trainer or model."""

import base64
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import time

ROOT = Path("/workspaces/quoridor")


def main():
    began = time.monotonic()
    stop = json.loads(
        (
            ROOT / "research-data/ai-sigma/frame24-trainer-observation/compact-source-stop-v2.json"
        ).read_text()
    )
    for binding in stop["bindings"]:
        data = (ROOT / binding["path"]).read_bytes()
        assert len(data) == binding["bytes"]
        assert hashlib.sha256(data).hexdigest() == binding["sha256"]
    fixture = (
        ROOT
        / "research-data/ai-sigma/frame24-trainer-observation/independent_metadata_fixture_308.py"
    )
    spec = importlib.util.spec_from_file_location("observer_metadata_fixture", fixture)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    import numpy as np

    env = {"np": np, "math": math, "json": json, "Path": Path, "hashlib": hashlib, "base64": base64}
    exec(module.extract(ROOT / "python/quoridor_training/common.py", ["measurements"]), env)
    exec(
        module.extract(
            ROOT / "python/quoridor_training/train.py", ["metrics", "write", "summarize"]
        ),
        env,
    )
    rows = [
        dict(group=g, z=z, rootmean=None)
        for g, z in [("a", 1), ("a", -1), ("b", 1), ("b", 1), ("c", 0), ("c", 0)]
    ]
    values = np.array([0.2, -0.6, 0.8, 0.1, 0.3, -0.2], dtype=np.float32)
    truth = np.array([r["z"] for r in rows], dtype=np.float32)
    with tempfile.TemporaryDirectory(
        dir=ROOT / "research-data/ai-sigma/frame24-coordinator"
    ) as tmp:
        env.update(
            rows=rows,
            target="z",
            constant=0.05,
            binding={"dataset_sha": "synthetic"},
            distances=np.zeros((6, 2), dtype=np.float32),
            distance_fit={"a": 0, "b": 8},
            measurement_sets={},
            reference_metrics={},
            labels=np.stack([np.zeros(6), truth], axis=1),
            column=1,
            output=Path(tmp),
        )
        report = env["summarize"](np.arange(6), values)
        vectors = report["groups"]["fields"]
        mse = np.frombuffer(base64.b64decode(vectors["target_mse"]), dtype="<f4")
        expected = np.array(
            [np.mean((values[i : i + 2] - truth[i : i + 2]) ** 2) for i in [0, 2, 4]]
        )
        assert np.max(np.abs(mse - expected)) <= 4 * np.finfo(np.float32).eps
        assert (
            abs(report["target_game_equal_mse"] - float(expected.mean()))
            <= 4 * np.finfo(np.float32).eps
        )
        sign = np.frombuffer(base64.b64decode(vectors["z_sign_accuracy"]), dtype="<f4")
        assert np.isnan(sign[2])
        before = (len(env["measurement_sets"]), len(env["reference_metrics"]))
        env["summarize"](np.arange(6), -values)
        assert before == (len(env["measurement_sets"]), len(env["reference_metrics"])) == (1, 1)
    result.update(
        independent_group_formula_PASS=True,
        static_references_once_PASS=True,
        missing_sign_NaN_PASS=True,
        bound_SOURCE_SHA_PASS=True,
        whole_command_body_seconds=time.monotonic() - began,
        acceptance="METADATA_PASS_ONLY; original live3PASS1ERROR and MAX remain unchanged",
    )
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
