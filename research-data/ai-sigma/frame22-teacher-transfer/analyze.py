"""Label-allowlisted saved teacher diagnostic; no model/framework import."""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import time


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def mean(values):
    return sum(values) / len(values) if values else None


def correlation(a, b):
    ma, mb = mean(a), mean(b)
    if ma is None:
        return None
    cross = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    return cross / math.sqrt(va * vb) if va * vb > 0 else None


def aggregate(rows):
    y = [r["rootmean"] for r in rows]
    z = [r["z"] for r in rows]
    d = [r["D"] for r in rows]
    groups = defaultdict(list)
    for r in rows:
        groups[r["group"]].append(r)
    return {
        "rows": len(rows),
        "groups": len(groups),
        "mean_rootmean": mean(y),
        "mean_z": mean(z),
        "rootmean_D_rowMSE": mean([(a - b) ** 2 for a, b in zip(y, d)]),
        "rootmean_D_gameMSE": mean(
            [mean([(r["rootmean"] - r["D"]) ** 2 for r in g]) for g in groups.values()]
        ),
        "z_D_gameMSE": mean([mean([(r["z"] - r["D"]) ** 2 for r in g]) for g in groups.values()]),
        "rootmean_z_gameMSE": mean(
            [mean([(r["rootmean"] - r["z"]) ** 2 for r in g]) for g in groups.values()]
        ),
        "corr_rootmean_z": correlation(y, z),
        "corr_rootmean_D": correlation(y, d),
        "rootmean_z_sign_agreement": mean([float(a * b > 0) for a, b in zip(y, z)]),
        "residual_mean": mean([a - b for a, b in zip(y, d)]),
        "residual_zcorr": correlation([a - b for a, b in zip(y, d)], z),
        "rootmean_abs_gt_09": sum(abs(v) >= 0.9 for v in y),
        "D_abs_gt_09": sum(abs(v) >= 0.9 for v in d),
        "D_rootmean_wrong_sign": sum(a * b < 0 for a, b in zip(y, d)),
        "D_z_wrong_sign": sum(a * b < 0 for a, b in zip(z, d)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intake", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    start = time.monotonic()
    sources = json.loads(Path(args.intake).read_text())["sources"]
    for name, item in sources.items():
        if name not in ("train", "validation", "labels", "mask"):
            raise ValueError("unregistered input")
        if hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("SHA mismatch")
    labels = {}
    with gzip.open(sources["labels"]["path"], "rt") as stream:
        for line in stream:
            row = json.loads(line)
            if row["split"] not in ("train", "validation") or row["id"] in labels:
                raise ValueError("test/duplicate labels")
            labels[row["id"]] = row
    mask = json.loads(Path(sources["mask"]["path"]).read_text())
    result = {}
    seen = set()
    partitions = {}
    for split, expected in (("train", 4653), ("validation", 1248)):
        rows = []
        signatures = {k: Counter() for k in ("state_key", "history_key", "QF1_input_sha256")}
        with gzip.open(sources[split]["path"], "rt") as stream:
            for line in stream:
                r = json.loads(line)
                label = labels[r["id"]]
                if r["split"] != split or label["split"] != split or r["id"] in seen:
                    raise ValueError("split/identity")
                seen.add(r["id"])
                mark = mask["rows"][r["id"]]
                if mark["split"] != split or mark["group"] != r["group"]:
                    raise ValueError("mask identity")
                if not mark["primary_eligible"]:
                    raise ValueError("unexpected excluded row: retain denominator")
                ds, do = (f32(v) for v in r["distance"])
                logit = f32(8.0 * f32(do - ds))
                prediction = f32(math.tanh(logit))
                ids = r["ids"][r["side"] - 1]
                left_self = [v - 290 for v in ids if 290 <= v < 301]
                left_opp = [v - 301 for v in ids if 301 <= v < 312]
                if len(left_self) != 1 or len(left_opp) != 1:
                    raise ValueError("remaining wall onehot")
                phase = "opening" if r["ply"] < 20 else "middle" if r["ply"] < 60 else "late"
                wall_bin = (
                    "0-5"
                    if sum(left_self + left_opp) <= 5
                    else ("6-12" if sum(left_self + left_opp) <= 12 else "13-20")
                )
                distance_bin = (
                    "near_goal"
                    if min(ds, do) <= 2 / 80
                    else ("balanced" if abs(do - ds) <= 1 / 80 else "separated")
                )
                rows.append(
                    {
                        **r,
                        **label,
                        "D": prediction,
                        "phase": phase,
                        "wall_bin": wall_bin,
                        "distance_bin": distance_bin,
                    }
                )
                for key in signatures:
                    signatures[key][r[key]] += 1
        if len(rows) != expected:
            raise ValueError("registered count")
        partitions[split] = rows
        summary = {"all": aggregate(rows), "groups": {}}
        for key in ("phase", "wall_bin", "distance_bin", "cohort", "group"):
            buckets = defaultdict(list)
            for r in rows:
                buckets[r[key]].append(r)
            summary[key] = {k: aggregate(v) for k, v in buckets.items()}
        summary["duplicate_signatures"] = {
            key: {"unique": len(v), "repeated_rows": sum(n - 1 for n in v.values())}
            for key, v in signatures.items()
        }
        summary["history_count"] = "NOT_RECORDED in canonical: history hash is not repetition count"
        result[split] = summary
    if seen != set(labels):
        raise ValueError("label join coverage")
    for key in ("state_key", "history_key", "QF1_input_sha256", "group"):
        a = {r[key] for r in partitions["train"]}
        b = {r[key] for r in partitions["validation"]}
        result.setdefault("cross_split_shared", {})[key] = len(a & b)
    result.update(
        {
            "task": "frame22-teacher-transfer-274-analysis-v1",
            "schema": "teacher-analysis-v1",
            "status": "PASS",
            "sources": sources,
            "science_samples_NN": 0,
            "rows_processed": 5901,
            "wall_seconds": time.monotonic() - start,
            "D_formula": "f32(tanh(f32(8*f32(f32(dopp)-f32(dself)))))",
            "test_read": False,
            "history_count_missing_not_imputed": True,
        }
    )
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
