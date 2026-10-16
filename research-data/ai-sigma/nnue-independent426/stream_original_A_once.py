"""Stream the twelve original426 archives once into compact observation summaries."""

import collections
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


def add_numbers(target, value, prefix=""):
    for key, child in value.items():
        path = prefix + key
        if isinstance(child, dict):
            add_numbers(target, child, path + ".")
        elif type(child) in (int, float):
            row = target.setdefault(path, {"n": 0, "min": child, "max": child})
            row["n"] += 1
            row["min"], row["max"] = min(row["min"], child), max(row["max"], child)
            gauge = any(
                word in key for word in ("bytes", "capacity", "slots", "entries")
            )
            if not gauge:
                row["sum"] = row.get("sum", 0) + child
            else:
                row["unit_note"] = "gauge, not additive"


def main():
    destination = HERE / "raw-observation-summary.json"
    if destination.exists():
        raise FileExistsError("original archive extraction already saved")
    inlet = load("inlet.json")["data"]
    collection = next(
        value
        for path, value in inlet.items()
        if path.endswith("/arena384-entry-v1/collection.json")
    )
    small = load("native-small-inlet.json")["data"]
    families = {x["analysis_family_index"]: x for x in load("families.json")}
    game_rows = {}
    import csv

    with (HERE / "games.csv").open() as source:
        for row in csv.DictReader(source):
            game_rows[int(row["global_slot"])] = row
    model = [
        {
            "model": name,
            "observations": 0,
            "accepted": 0,
            "accepted_completed": 0,
            "depth_hist": collections.Counter(),
            "depth_by_side": {0: collections.Counter(), 1: collections.Counter()},
            "stops": collections.Counter(),
            "scalar_fields": {},
            "selected_snapshot_work": {},
            "whole_search_work_alternative": {},
            "receipt_checked": 0,
            "receipt_late": 0,
            "return_checked": 0,
            "return_after_deadline": 0,
            "commit_checked": 0,
            "commit_after_deadline": 0,
            "accepted_authority_legal_false": 0,
            "accepted_authority_legal_unknown": 0,
            "caller_seconds": [],
            "thinking_seconds": [],
        }
        for name in ("W", "BEST43")
    ]
    receipts, per_game, examples, discrepancies = [], [], [], []
    schema = None
    for batch in collection["batches"]:
        index = batch["index"]
        reference = batch["native_archive"]
        path = Path(reference["path"])
        before = path.stat()
        if before.st_size != reference["bytes"] or before.st_size > 4 * 1024**2:
            raise ValueError("bounded original archive size changed")
        with path.open("rb") as stream:
            compressed = stream.read(4 * 1024**2 + 1)
        if hashlib.sha256(compressed).hexdigest() != reference["sha256"]:
            raise ValueError("original archive hash mismatch before decode")
        raw_hash, raw_bytes, records = hashlib.sha256(), 0, 0
        native = next(
            value
            for p, value in small.items()
            if p.endswith(f"/batch-{index:03d}/data/result.json")
        )
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as archive:
            while True:
                line = archive.readline(2 * 1024**2 + 1)
                if not line:
                    break
                if len(line) > 2 * 1024**2:
                    raise ValueError("bounded original game record exceeded")
                raw_hash.update(line)
                raw_bytes += len(line)
                game = json.loads(line)
                local = int(game["game"])
                slot = index * 32 + local
                row = game_rows[slot]
                family = families[int(row["analysis_family_index"])]
                prefix = family["prefix"]
                if (
                    game["candidate_color"] != int(row["candidate_color"])
                    or game["winner"] != int(row["winner"])
                    or game["moves"][: len(prefix)] != prefix
                    or len(game["moves"]) != int(row["reported_plies"])
                ):
                    discrepancies.append({"slot": slot, "scope": "game/CSV/prefix"})
                observations = game["observations"]
                if schema is None:
                    first = observations[0]
                    schema = {
                        "game_keys": list(game),
                        "observation_keys": list(first),
                        "counter_keys": list(first["counters"]),
                        "whole_search_keys": list(
                            first["counters"].get("whole_search", {})
                        ),
                        "selected_work_keys": list(
                            first.get("completed_iteration_counters") or {}
                        ),
                    }
                accepted = 0
                for observation in observations:
                    actor = observation["engine_index"]
                    if actor not in (0, 1):
                        raise ValueError("unknown actual engine index")
                    target = model[actor]
                    side = observation["side"]
                    expected_actor = 0 if side == game["candidate_color"] else 1
                    if actor != expected_actor:
                        discrepancies.append({"slot": slot, "scope": "actor/colour"})
                    target["observations"] += 1
                    target["stops"][str(observation.get("stop"))] += 1
                    counters = observation["counters"]
                    for scope, fields in [
                        ("observation", observation),
                        ("counters", counters),
                    ]:
                        for key, value in fields.items():
                            if isinstance(value, (dict, list)) or type(value) in (
                                int,
                                float,
                            ):
                                continue
                            if (
                                value is None
                                or isinstance(value, bool)
                                or (isinstance(value, str) and len(value) <= 180)
                            ):
                                counts = target["scalar_fields"].setdefault(
                                    scope + "." + key, collections.Counter()
                                )
                                counts[str(value)] += 1
                    whole = counters.get("whole_search")
                    if isinstance(whole, dict):
                        add_numbers(target["whole_search_work_alternative"], whole)
                    selected = observation.get("completed_iteration_counters")
                    if isinstance(selected, dict):
                        add_numbers(target["selected_snapshot_work"], selected)
                    deadline = observation.get("deadline_ns")
                    for name, stamp in [
                        ("receipt", counters.get("authority_receipt_ns")),
                        ("return", observation.get("returned_ns")),
                        ("commit", counters.get("state_commit_ns")),
                    ]:
                        if type(deadline) is int and type(stamp) is int:
                            target[name + "_checked"] += 1
                            key = (
                                "receipt_late"
                                if name == "receipt"
                                else name + "_after_deadline"
                            )
                            target[key] += stamp > deadline
                    if observation.get("accepted"):
                        accepted += 1
                        target["accepted"] += 1
                        legal = counters.get("authority_legal")
                        target["accepted_authority_legal_false"] += legal is False
                        target["accepted_authority_legal_unknown"] += legal is None
                        depth = observation.get("completed_depth")
                        if type(depth) is int:
                            target["accepted_completed"] += 1
                            target["depth_hist"][depth] += 1
                            target["depth_by_side"][side][depth] += 1
                    for key in ["caller_seconds", "thinking_seconds"]:
                        value = observation.get(key)
                        if type(value) in (int, float):
                            target[key].append(value)
                if accepted != len(game["moves"]) - len(prefix):
                    discrepancies.append(
                        {"slot": slot, "scope": "accepted/moves", "accepted": accepted}
                    )
                per_game.append(
                    {
                        "slot": slot,
                        "analysis_family_index": family["analysis_family_index"],
                        "batch": index,
                        "local_game": local,
                        "archive_line": records + 1,
                        "raw_line_sha256": hashlib.sha256(line).hexdigest(),
                        "raw_line_bytes": len(line),
                        "observations": len(observations),
                        "accepted": accepted,
                        "prefix_plies": len(prefix),
                        "total_plies": len(game["moves"]),
                    }
                )
                if slot in (0, 1):
                    first = observations[0]
                    examples.append(
                        {
                            "selection": "first two global slots, not replaced by outcome",
                            "slot": slot,
                            "family": 0,
                            "prefix": prefix,
                            "archive": reference,
                            "line": records + 1,
                            "line_sha256": hashlib.sha256(line).hexdigest(),
                            "engine_index": first["engine_index"],
                            "ply": first["ply"],
                            "side": first["side"],
                            "action": first["action"],
                            "value_STM": first["value_stm"],
                            "completed_depth": first["completed_depth"],
                            "PV": first["pv"],
                            "accepted": first["accepted"],
                            "following_actions": game["moves"][
                                len(prefix) : len(prefix) + 8
                            ],
                            "winner": game["winner"],
                            "stop": first.get("stop"),
                            "caller_seconds": first.get("caller_seconds"),
                            "thinking_seconds": first.get("thinking_seconds"),
                        }
                    )
                records += 1
        expected_archive = native["archive"]
        if (
            raw_hash.hexdigest() != expected_archive["raw_sha256"]
            or raw_bytes != expected_archive["raw_bytes"]
        ):
            raise ValueError("original raw content changed")
        if records != 32:
            raise ValueError("original archive census differs")
        with path.open("rb") as stream:
            final_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        after = path.stat()
        if (
            final_hash != reference["sha256"]
            or after.st_size != before.st_size
            or after.st_mode != before.st_mode
        ):
            raise ValueError("original archive changed after one decode")
        receipts.append(
            {
                "archive": reference,
                "raw_sha256": raw_hash.hexdigest(),
                "raw_bytes": raw_bytes,
                "records": records,
                "CRC_EOF": "PASS",
                "decode_count": 1,
                "before_after_MATCH": True,
            }
        )
    for target in model:
        depths = list(target["depth_hist"].elements())
        target["accepted_depth"] = {
            "n": len(depths),
            "mean": statistics.mean(depths) if depths else None,
            "median": statistics.median(depths) if depths else None,
            "min": min(depths) if depths else None,
            "max": max(depths) if depths else None,
        }
        for name in ["caller_seconds", "thinking_seconds"]:
            values = target[name]
            target[name] = {
                "n": len(values),
                "sum": sum(values),
                "median": statistics.median(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "scope": "alternative nested clocks, not additive",
            }
    summary = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "archives": receipts,
        "record_count": len(per_game),
        "model": model,
        "per_game": per_game,
        "schema": schema,
        "discrepancies": discrepancies,
        "selected_vs_whole": "alternative overlapping views, never added",
        "TT_gauges": "no sum",
        "physical_NN_or_continuous_RSS": "UNKNOWN",
        "new_Search_forward_game_solver_fit": 0,
    }
    destination.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (HERE / "first-family-observations.json").write_text(
        json.dumps(examples, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "records": len(per_game),
                "archives_decoded_once": len(receipts),
                "discrepancies": discrepancies,
                "schema": schema,
                "models": [
                    {
                        k: v
                        for k, v in x.items()
                        if k
                        not in [
                            "selected_snapshot_work",
                            "whole_search_work_alternative",
                        ]
                    }
                    for x in model
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
