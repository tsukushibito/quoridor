"""NN0 record preparation only: does not search, fit, or enable ProbCut."""

import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BINDINGS = ("model_sha", "scale_sha", "rules_sha", "search_sha", "calibration_version")
TACTICS = ("immediate_goal", "forced_defense", "jump", "wall_block")


def partition(group, split_version):
    """Keep a family and all related input views in one prelabel partition."""
    digest = hashlib.sha256(f"{split_version}:{group}".encode()).digest()
    return (
        "unused_validation"
        if int.from_bytes(digest[:8], "little") % 4 == 0
        else "calibration"
    )


def namespace(binding, mode, origin):
    if mode not in ("OFF", "ON") or origin not in ("FULL_WIDTH", "MPC_APPROXIMATE"):
        raise ValueError("namespace enum")
    if mode == "OFF" and origin != "FULL_WIDTH":
        raise ValueError("approximate bound cannot enter OFF exact TT")
    return hashlib.sha256(
        json.dumps([binding, mode, origin], sort_keys=True).encode()
    ).hexdigest()


def validate(record):
    for key in (*BINDINGS, "input_sha", "history_sha", "group", "split_version"):
        if not isinstance(record.get(key), str) or not record[key]:
            raise ValueError(f"missing binding: {key}")
    if record.get("mpc_mode") != "OFF" or record.get("tt_origin") != "FULL_WIDTH":
        raise ValueError("calibration must be MPC-OFF full-width")
    if record.get("extensions_reductions") != "DISABLED":
        raise ValueError("full-width depth meaning not bound")
    if record.get("side") not in (1, 2) or type(record["side"]) is not int:
        raise ValueError("actual STM side")
    shallow, deep = record["shallow"], record["deep"]
    if not (0 < shallow["requested_depth"] < deep["requested_depth"]):
        raise ValueError("depth pair")
    if record.get("partition") != partition(record["group"], record["split_version"]):
        raise ValueError("prelabel group partition")
    if any(type(record["tactical"].get(t)) not in (bool, type(None)) for t in TACTICS):
        raise ValueError("tactical tri-state")
    reasons = []
    for label, score in (("shallow", shallow), ("deep", deep)):
        status = score["status"]
        if status == "UNKNOWN":
            if score["value"] is not None:
                raise ValueError("capped UNKNOWN cannot supply adopted value")
            reasons.append(f"{label}_INCOMPLETE")
            continue
        if status != "COMPLETED":
            raise ValueError("completion enum")
        if (
            score["completed_depth"] != score["requested_depth"]
            or score["bound"] != "EXACT"
        ):
            raise ValueError("completed full-window exact root required")
        if score["window"] != [-2.1, 2.1]:
            raise ValueError("full root window")
        value = score["value"]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("finite score")
        if score["origin"] == "TERMINAL":
            if value not in (-2, 0, 2):
                raise ValueError("terminal scale")
            reasons.append(f"{label}_TERMINAL_BYPASS")
        elif score["origin"] == "NONTERMINAL":
            if not -1 <= value <= 1:
                raise ValueError("nonterminal scale")
        else:
            reasons.append(f"{label}_ORIGIN_UNAVAILABLE")
        for cost in ("processed", "NN", "wall_s"):
            if (
                type(score.get(cost)) not in (int, float)
                or not math.isfinite(score[cost])
                or score[cost] < 0
            ):
                raise ValueError("missing measured cost")
    for tactic in TACTICS:
        if record["tactical"][tactic] is not False:
            reasons.append(f"{tactic}_BYPASS_OR_UNVERIFIED")
    return {"fit_eligible": not reasons, "reasons": reasons, "policy_enabled": False}


def fixture():
    score = {
        "requested_depth": 1,
        "completed_depth": 1,
        "status": "COMPLETED",
        "bound": "EXACT",
        "window": [-2.1, 2.1],
        "value": 0.1,
        "origin": "NONTERMINAL",
        "processed": 0,
        "NN": 0,
        "wall_s": 0,
    }
    r = {k: "SYNTHETIC_NOT_SCIENCE" for k in BINDINGS}
    r.update(
        {
            "input_sha": "SYNTHETIC",
            "history_sha": "SYNTHETIC",
            "group": "fake-family",
            "split_version": "mpc-group-split-v1",
            "side": 2,
            "mpc_mode": "OFF",
            "tt_origin": "FULL_WIDTH",
            "extensions_reductions": "DISABLED",
            "tactical": dict.fromkeys(TACTICS, False),
            "shallow": score,
            "deep": {**score, "requested_depth": 2, "completed_depth": 2, "value": 0.2},
        }
    )
    r["partition"] = partition(r["group"], r["split_version"])
    return r


def checks():
    base = fixture()
    results = []
    assert validate(base)["fit_eligible"]
    results.append("synthetic completed paired input accepted, policy remains OFF")
    for mutation in (
        lambda r: r.update(mpc_mode="ON"),
        lambda r: r.update(tt_origin="MPC_APPROXIMATE"),
        lambda r: r["deep"].update(completed_depth=1),
        lambda r: r["deep"].update(bound="LOWER"),
        lambda r: r["deep"].update(value=float("nan")),
        lambda r: r["deep"].update(value=2),
        lambda r: r["deep"].update(status="UNKNOWN"),
        lambda r: r.update(history_sha=""),
        lambda r: r.update(partition="incorrect"),
    ):
        r = copy.deepcopy(base)
        mutation(r)
        try:
            validate(r)
        except ValueError:
            results.append("invalid synthetic rejected")
        else:
            raise AssertionError("invalid record accepted")
    for tactic in TACTICS:
        r = copy.deepcopy(base)
        r["tactical"][tactic] = True
        assert not validate(r)["fit_eligible"]
        results.append(f"{tactic} bypass")
    r = copy.deepcopy(base)
    r["deep"].update(status="UNKNOWN", value=None, completed_depth=1)
    assert not validate(r)["fit_eligible"]
    results.append("capped null score preserved, not fitted")
    r = copy.deepcopy(base)
    r["deep"].update(origin="TERMINAL", value=-2)
    assert not validate(r)["fit_eligible"]
    results.append("terminal scale separated from regression")
    key = {k: base[k] for k in BINDINGS}
    assert namespace(key, "OFF", "FULL_WIDTH") != namespace(
        key, "ON", "MPC_APPROXIMATE"
    )
    try:
        namespace(key, "OFF", "MPC_APPROXIMATE")
    except ValueError:
        results.append("approximate OFF TT refused")
    else:
        raise AssertionError("approximate OFF namespace")
    return results


if __name__ == "__main__":
    result = {
        "task": "mpc-calibration-preparation-306-v1",
        "schema": "mpc-preparation-fixtures-v1",
        "checks": checks(),
        "NN": 0,
        "science_MAX": 0,
        "synthetic_only": True,
        "calibration_fit": "NOT_RUN",
        "core_implementation": "NOT_IMPLEMENTED",
        "policy_enabled": False,
    }
    (ROOT / "fixture-result-v1.json").write_text(json.dumps(result, indent=2) + "\n")
