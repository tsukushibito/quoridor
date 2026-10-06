"""Coordinator-only AST/stdlib metadata fixture, no trainer/model import."""

import ast
import base64
import copy
import gzip
import io
import json
import math
from pathlib import Path
import random
import struct
import tempfile
import time


def extract(path, names):
    tree = ast.parse(Path(path).read_text())
    nodes = []
    for name in names:
        found = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
        assert len(found) == 1
        nodes.append(found[0])
    return compile(
        ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(path), "exec"
    )


def run():
    started = time.monotonic()
    path = Path("python/quoridor_training/train.py")
    env = {"json": json, "time": time, "Path": Path, "phase_seconds": {"logging": 0.0}}
    exec(extract(path, ["append_record", "curve_summary", "_plot"]), env)
    stream = io.StringIO()
    for i in range(2):
        env["append_record"](stream, {"step": i, "status": "COMPLETED"})
    assert [json.loads(v)["step"] for v in stream.getvalue().splitlines()] == [0, 1]
    good = []
    for line in (stream.getvalue() + '{"step":').splitlines():
        try:
            good.append(json.loads(line))
        except json.JSONDecodeError:
            break
    assert len(good) == 2
    rec = {"step": 1, "train": {"groups": {}}, "validation": {"groups": {}}}
    assert "groups" not in env["curve_summary"](rec, "full_selector")["train"]
    common = Path("python/quoridor_training/common.py")
    tree = ast.parse(common.read_text())
    defaults = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "DEFAULTS" for t in n.targets)
    )
    cfg_env = {"copy": copy, "json": json, "math": math, "Path": Path}
    exec(compile(ast.Module(body=[defaults], type_ignores=[]), "common", "exec"), cfg_env)
    exec(extract(common, ["resolve_config"]), cfg_env)
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty.svg"
        env["_plot"]([], empty)
        assert "\n" in empty.read_text() and "<polyline" not in empty.read_text()
        cfg = Path(tmp) / "config.json"
        cfg.write_text(
            json.dumps(
                {
                    "training": {"steps": 20},
                    "evaluation": {"checkpoints": [0, 20], "full_train_checkpoints": [0, 20]},
                }
            )
        )
        assert cfg_env["resolve_config"](cfg)["artifacts"]["checkpoint_steps"] == []
        try:
            cfg_env["resolve_config"](cfg, ["training.steps=5"])
        except ValueError:
            pass
        else:
            raise AssertionError("override not revalidated")
    text = path.read_text()
    assert "if step in checkpoint_steps:" in text and "if (selector and scheduled)" not in text
    assert '"<f4"' in text and '"order_ref": scope' in text
    assert 'or step in cfg["evaluation"]["full_train_checkpoints"]' in text
    raw = struct.pack("<4f", 0.0, 1.0, math.nan, -2.0)
    back = struct.unpack("<4f", base64.b64decode(base64.b64encode(raw)))
    assert back[:2] == (0.0, 1.0) and math.isnan(back[2]) and back[3] == -2.0
    rng = random.Random(308)
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=1) as z:
        for step in range(400):
            record = {"step": step}
            for scope, count in [("train", 432), ("validation", 144)]:
                fields = {}
                for field in ["target_mse", "z_sign_accuracy", "saturation_fraction", "bias"]:
                    values = [
                        rng.randrange(201) / 200
                        if field in ("z_sign_accuracy", "saturation_fraction")
                        else rng.random() * 4
                        for _ in range(count)
                    ]
                    fields[field] = base64.b64encode(
                        struct.pack("<" + "f" * count, *values)
                    ).decode()
                record[scope] = {"order_ref": "a" * 64, "fields": fields}
            z.write((json.dumps(record) + "\n").encode())
            z.flush()
    groups = len(out.getvalue())
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=1) as z:
        for step in range(8000):
            record = {
                "step": step,
                "status": "COMPLETED",
                "training_seen": step * 128,
                "wall_seconds": rng.random() * 90,
                "objective_loss": rng.random(),
                "batch_row_mse": rng.random(),
                "lr": [0.0001],
                "batch_rows": 128,
                "samples": step * 128,
                "gradient_norm": {str(k): rng.random() * 100 for k in range(6)},
            }
            z.write((json.dumps(record) + "\n").encode())
            z.flush()
    batches = len(out.getvalue())
    total = groups + batches + 2 * 1024**2
    return {
        "status": "AST_STDLIB_METADATA_PASS",
        "model_imports": 0,
        "NN": 0,
        "group400point_B": groups,
        "batch8000point_B": batches,
        "other_inclusive_forecast_B": 2 * 1024**2,
        "two_cases_forecast_B": total,
        "within6MiB": total < 6291456,
        "bound_assumptions": "known native group<=200rows; fourf32vectors; synthetic forecast not universal compression proof; actual+remaining guard required",
        "wall_seconds": time.monotonic() - started,
    }


if __name__ == "__main__":
    print(json.dumps(run()))
