"""295 separate saved arithmetic; old291 failed scientific bytes unchanged."""

import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

ROOT = Path("/workspaces/quoridor")
OUT = ROOT / "research-data/ai-sigma/frame23-frozen-z-saved-arithmetic/result-r1"
TASK = "frozen-z-saved-arithmetic-295-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonlines(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def metrics(rows, np):
    if not rows:
        return {
            model: {
                "rowweighted": {key: None for key in ("MSE", "sign", "bias", "saturation")},
                "groupequal": {key: None for key in ("MSE", "sign", "bias", "saturation")},
                "pergroup": [],
                "calibration_bins": [],
                "status": "UNDEFINED_ZERO_ELIGIBLE",
            }
            for model in ("candidate", "D", "constant")
        }
    families = {}
    for row in rows:
        families.setdefault(row["family"], []).append(row)
    result = {}
    for model in ("candidate", "D", "constant"):
        pergroup = []
        for family, group in sorted(families.items()):
            p = np.asarray([r["prediction"][model] for r in group], dtype="<f8")
            z = np.asarray([r["z"] for r in group], dtype="<f8")
            pergroup.append(
                {
                    "family": family,
                    "rows": len(group),
                    "MSE": float(np.mean((p - z) ** 2)),
                    "sign": float(np.mean(np.sign(p) == np.sign(z))),
                    "bias": float(np.mean(p - z)),
                    "saturation": float(np.mean(np.abs(p) >= 0.99)),
                    "z_mean": float(z.mean()),
                }
            )
        p = np.asarray([r["prediction"][model] for r in rows], dtype="<f8")
        z = np.asarray([r["z"] for r in rows], dtype="<f8")
        bins = []
        for lower, upper in zip((-1.0, -0.6, -0.2, 0.2, 0.6), (-0.6, -0.2, 0.2, 0.6, 1.0)):
            selected = (p >= lower) & ((p < upper) if upper < 1 else (p <= upper))
            bins.append(
                {
                    "lower": lower,
                    "upper": upper,
                    "rows": int(selected.sum()),
                    "mean_prediction": float(p[selected].mean()) if selected.any() else None,
                    "mean_z": float(z[selected].mean()) if selected.any() else None,
                }
            )
        result[model] = {
            "rowweighted": {
                "MSE": float(np.mean((p - z) ** 2)),
                "sign": float(np.mean(np.sign(p) == np.sign(z))),
                "bias": float(np.mean(p - z)),
                "saturation": float(np.mean(np.abs(p) >= 0.99)),
            },
            "groupequal": {
                key: float(np.mean([g[key] for g in pergroup]))
                for key in ("MSE", "sign", "bias", "saturation")
            },
            "pergroup": pergroup,
            "calibration_bins": bins,
        }
    return result


def native_goal(game):
    assert game["status"] == "goal" and game["terminal_reason"] == "GOAL"
    assert game["winner_absolute0or1"] in (0, 1)


def public_label(value):
    assert value in (-1.0, 0.0, 1.0)
    return value != 0.0


def unique_keys(rows):
    keys = [(r["family"], r["id"]) for r in rows]
    assert len(keys) == len(set(keys))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    assert reg["task"] == TASK and reg["entry_SHA"] == sha(__file__)
    if args.mock:
        import sys

        assert sys.argv.count(str(Path(args.registration))) == 1
        native_goal({"status": "goal", "terminal_reason": "GOAL", "winner_absolute0or1": 0})
        rejected = 0
        for bad in [
            {"status": "GOAL", "terminal_reason": "GOAL", "winner_absolute0or1": 0},
            {"status": "goal", "terminal_reason": "goal", "winner_absolute0or1": 0},
            {"status": "unknown", "terminal_reason": "GOAL", "winner_absolute0or1": 0},
        ]:
            try:
                native_goal(bad)
            except AssertionError:
                rejected += 1
        assert rejected == 3
        assert not public_label(0.0) and public_label(-1.0) and public_label(1.0)
        for bad in [float("nan"), float("inf"), 2.0, 0.5]:
            try:
                public_label(bad)
            except AssertionError:
                pass
            else:
                raise AssertionError("wrong finite/NaN label accepted")
        unique_keys([{"family": "A", "id": "1"}, {"family": "B", "id": "1"}])
        try:
            unique_keys([{"family": "A", "id": "1"}, {"family": "A", "id": "1"}])
        except AssertionError:
            pass
        else:
            raise AssertionError("duplicate join accepted")
        assert sum(public_label(z) for z in [0.0, 1.0]) == 1
        assert all(v["status"] == "UNDEFINED_ZERO_ELIGIBLE" for v in metrics([], None).values())
        print(
            json.dumps(
                {"task": TASK, "argument_registration_PASS": True, "NN": 0, "labels_read": False}
            )
        )
        return
    OUT.mkdir(exist_ok=False)
    start = time.monotonic()
    for path, expected in reg["inputs"].items():
        assert sha(path) == expected
    freeze = json.loads(Path(reg["evaluation_freeze"]).read_text())
    release = json.loads(Path(reg["label_release"]).read_text())
    assert release["independent_eval_mask_freeze"]["SHA"] == sha(reg["evaluation_freeze"])
    assert release["candidate_freeze"]["SHA"] == freeze["candidate_freeze_SHA"]
    assert freeze["no_reselection_no_refill_no_added_model"]
    rows = read_jsonlines(reg["predictions"])
    predictions = {(r["domain"], r["family"], r["id"]): r for r in rows}
    assert len(predictions) == len(rows) == 5257
    for domain in ("public0043", "RuleA48"):
        unique_keys([r for r in rows if r["domain"] == domain])
    import numpy as np

    # Fixed train-only constant verification, with no evaluation labels in the fit.
    train_ids = {
        r["id"] for r in read_jsonlines(freeze["reference_bindings"]["Tseen"]["canonical"]["path"])
    }
    train_cache = Path(reg["train_cache"])
    train_labels = np.frombuffer((train_cache / "labels.f32").read_bytes(), dtype="<f4").reshape(
        -1, 2
    )
    train_z = []
    with (train_cache / "rows.jsonl").open() as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            if row["id"] in train_ids:
                train_ids.remove(row["id"])
                z = float(train_labels[index, 1])
                assert z in (-1.0, 1.0)
                train_z.append(z)
    assert not train_ids and len(train_z) == 67937
    constant = float(np.mean(train_z))
    assert abs(constant - freeze["baselines"]["constant"]["value"]) < 1e-12

    public_release = release["public0043"]
    cache = Path(public_release["cache_manifest"]["path"])
    manifest = json.loads(cache.read_text())
    assert sha(cache) == public_release["cache_manifest"]["SHA"]
    assert manifest["rows"] == 19359 and manifest["feature_count"] == 312
    labels_path, rows_path = cache.parent / "labels.f32", cache.parent / "rows.jsonl"
    assert sha(labels_path) == manifest["sha256"]["labels.f32"]
    assert sha(rows_path) == manifest["sha256"]["rows.jsonl"]
    labels = np.frombuffer(labels_path.read_bytes(), dtype="<f4").reshape(-1, 2)
    assert len(labels) == 19359 and np.isnan(labels[:, 0]).all()
    public_masks = {
        (r["family"], r["id"]): r
        for r in read_jsonlines(freeze["masks"]["public0043"]["mask_path"])
    }
    public_targets = []
    counts = Counter()
    ids = set()
    public_seen_groups = set()
    public_excluded_zero_by_group = Counter()
    with rows_path.open() as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            key = (row["group"], row["id"])
            assert row["id"] not in ids
            ids.add(row["id"])
            mask = public_masks.pop(key)
            z = float(labels[index, 1])
            public_label(z)
            assert float(row["z"]) == z
            assert row["rootmean"] is None and row["split"] == "test"
            counts["raw_rows"] += 1
            counts["raw_reason_unknown_zero"] += z == 0
            counts["raw_decisive"] += z != 0
            public_seen_groups.add(row["group"])
            if not mask["eligible_input"]:
                counts["input_exposure_excluded"] += 1
                continue
            counts["input_eligible_rows"] += 1
            pred = predictions.pop(("public0043", row["group"], row["id"]))
            assert pred["input_signature"] == mask["input_signature"]
            if z == 0:
                counts["input_eligible_reason_unknown_zero_excluded"] += 1
                public_excluded_zero_by_group[row["group"]] += 1
                continue
            assert row["primary_eligible"]
            public_targets.append(pred | {"z": z})
    assert not public_masks and len(ids) == 19359
    assert len(public_seen_groups) == 10
    rule_release = release["rulea"]
    familymap = json.loads(Path(rule_release["family_map"]["path"]).read_text())
    provenance = json.loads(Path(rule_release["game_provenance"]["path"]).read_text())
    assert sha(rule_release["family_map"]["path"]) == rule_release["family_map"]["SHA"]
    assert sha(rule_release["game_provenance"]["path"]) == rule_release["game_provenance"]["SHA"]
    aliases = {r["native_family"]: r["canonical_family"] for r in familymap["families"]}
    games = {r["canonical_family"]: r for r in provenance["games"]}
    assert len(aliases) == len(games) == 48
    assert len({r["game_UID"] for r in games.values()}) == 48
    scalar_path = Path(rule_release["scalars"]["path"])
    assert sha(scalar_path) == rule_release["scalars"]["SHA"]
    digest = hashlib.sha256()
    rule_targets = []
    scalar_keys = set()
    status = Counter(g["status"] for g in games.values())
    with gzip.open(scalar_path, "rb") as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            family = aliases[row["native_family"]]
            key = (family, row["id"])
            assert key not in scalar_keys
            scalar_keys.add(key)
            pred = predictions.pop(("RuleA48", family, row["id"]))
            game = games[family]
            native_goal(game)
            expected = 1.0 if game["winner_absolute0or1"] + 1 == pred["side"] else -1.0
            assert float(row["z"]) == expected
            rule_targets.append(pred | {"z": expected})
    assert digest.hexdigest() == rule_release["scalars"]["uncompressed_SHA"]
    assert len(scalar_keys) == len(rule_targets) == 1668 and not predictions
    assert len({r["family"] for r in rule_targets}) == 48
    results = {"public0043": metrics(public_targets, np), "RuleA48": metrics(rule_targets, np)}
    pairs = {}
    for a, b in (("candidate", "D"), ("candidate", "constant"), ("D", "constant")):
        for metric in ("MSE", "sign"):
            aa, bb = results["RuleA48"][a]["pergroup"], results["RuleA48"][b]["pergroup"]
            assert [g["family"] for g in aa] == [g["family"] for g in bb]
            delta = np.asarray([x[metric] - y[metric] for x, y in zip(aa, bb)])
            rng = np.random.default_rng(29180311)
            draws = np.mean(delta[rng.integers(0, 48, size=(2000, 48))], axis=1)
            pairs[f"{a}minus{b}:{metric}"] = {
                "mean": float(delta.mean()),
                "95percentile": np.quantile(draws, [0.025, 0.975]).tolist(),
                "negative": int((delta < 0).sum()),
                "zero": int((delta == 0).sum()),
                "positive": int((delta > 0).sum()),
                "families": 48,
                "seed": 29180311,
                "repetitions": 2000,
                "fixedfits": True,
                "cohort_correlation_limit": True,
            }
    groups = {}
    for kind in ("cohort", "side", "phase"):
        bins = {}
        for row in rule_targets:
            value = (
                ("early" if row["ply"] < 20 else "middle" if row["ply"] < 60 else "late")
                if kind == "phase"
                else str(row[kind])
            )
            bins.setdefault(value, []).append(row)
        groups[kind] = {key: metrics(values, np) for key, values in bins.items()}
    result = {
        "task": TASK,
        "schema": "frozen-public-rulea-z-arithmetic-295-v1",
        "PASS": True,
        "UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "NN": 0,
        "model_forward": False,
        "train_only_constant_verification": {"rows": len(train_z), "mean": constant, "PASS": True},
        "futurelabels_read": True,
        "public_counts": dict(counts),
        "public_planned_groups": 10,
        "public_metric_rows": len(public_targets),
        "public_metric_inputgroups": len({r["family"] for r in public_targets}),
        "public_zeroeligible_groups": 10 - len({r["family"] for r in public_targets}),
        "public_zero_excluded_per_group": dict(public_excluded_zero_by_group),
        "public_independent_game_CI": "UNDEFINED",
        "public_phase_absoluteP2_history_game": "UNAVAILABLE",
        "RuleA_planned_families": 48,
        "RuleA_status": dict(status),
        "RuleA_terminal_reason": "GOAL",
        "old291_MAX2_failure_NOT_RUN_preserved": True,
        "RuleA_metric_rows": 1668,
        "RuleA_zeroeligible_families": 0,
        "RuleA_true_draw_games": 0,
        "winner_to_STM_z_independent_arithmetic": True,
        "sharedRuleA_teachertruth_dependency": True,
        "results": results,
        "RuleA_paired": pairs,
        "RuleA_groups": groups,
        "body_seconds": time.monotonic() - start,
        "entry_SHA": sha(__file__),
        "registration_SHA": sha(args.registration),
        "frozen_evaluation_SHA": sha(reg["evaluation_freeze"]),
        "limits": [
            "Public recorded +/-1 outcomes and native qualified input are conditional evidence, not certified complete legal game trajectories",
            "2 public retained inputgroups are not independent games; no game CI inferred",
            "RuleA48 fixed cohorts/opening distribution/family correlation; conditional fixedfits bootstrap not universal precision guarantee",
            "Source reader/native model finite parity/sharedRuleA dependencies, not full deep truth or samewall strength",
            "No test-result reselection/refill/retraining/arena; public and RuleA denominators kept separate",
        ],
    }
    with gzip.open(OUT / "result-v1.json.gz", "wt") as stream:
        json.dump(result, stream, separators=(",", ":"))
    summary = {k: v for k, v in result.items() if k not in ("results", "RuleA_groups")}
    summary["metrics"] = {
        domain: {
            model: {"rowweighted": value["rowweighted"], "groupequal": value["groupequal"]}
            for model, value in domainresults.items()
        }
        for domain, domainresults in results.items()
    }
    (OUT / "result-v1.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("RuleA_paired", "limits")}))


if __name__ == "__main__":
    main()
