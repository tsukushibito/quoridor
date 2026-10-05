"""Bind immutable native training shards, label-independent split and OR masks."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import struct
import time

import numpy as np

ROOT = Path("/workspaces/quoridor")
SCOPE = ROOT / "research-data/ai-sigma/frame23-native-outcome-z-learning"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for body in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(body)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def input_signature(ids, bits):
    body = [np.asarray(view, dtype="<u2").tobytes() for view in ids]
    key = b"QF1-f32-STM-v1\0" + struct.pack("<HH", len(body[0]), len(body[1]))
    return hashlib.sha256(
        key + b"".join(body) + np.asarray(bits, dtype="<u4").tobytes()
    ).hexdigest()


def load_public_private(block):
    for name, digest_name in (
        ("public_metadata", "public_SHA"),
        ("private_input_only_witness", "private_input_only_SHA"),
    ):
        if sha(block[name]) != block[digest_name]:
            raise ValueError("immutable input projection SHA: " + name)
    public, private = {}, {}
    for path, target in (
        (block["public_metadata"], public),
        (block["private_input_only_witness"], private),
    ):
        with Path(path).open() as stream:
            for line in stream:
                row = json.loads(line)
                if any(k in row for k in ("z", "rootmean", "winner", "prediction", "loss")):
                    raise ValueError("input projection contains forbidden label fields")
                if row["id"] in target:
                    raise ValueError("duplicate projection ID")
                target[row["id"]] = row
    if set(public) != set(private):
        raise ValueError("public/private input ID denominator")
    return public, private


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    regpath = Path(parser.parse_args().registration)
    reg = read(regpath)
    if reg["task"] != "native-z-input-preparation-298-v1":
        raise ValueError("wrong task")
    started = time.monotonic()
    for path, digest in reg["input_SHA"].items():
        if sha(path) != digest:
            raise ValueError("input/source changed: " + path)
    split = read(reg["split"])
    assignment = {f["canonical_family"]: f for f in split["families"]}
    handoff = read(reg["handoff"])
    blocks = [b for b in handoff["blocks"] if b["partition"] == "train" and 0 <= b["block"] < 12]
    if [b["block"] for b in blocks] != list(range(12)):
        raise ValueError("only complete original T0..11 permitted")
    raw_refs, shard_data, outcomes_seen, references = [], [], {}, []
    witness = []
    for block in blocks:
        public, private = load_public_private(block)
        path = Path(block["cache"])
        expected = (
            ROOT
            / ".worktree/assets/inputs/frame23-independent-teachers/v2/train"
            / f"block{block['block']:02d}-r1-cache"
        )
        if path != expected or sha(path / "cache.json") != block["cache_manifest_SHA"]:
            raise ValueError("original training cache path/SHA")
        namespace = f"frame23-285-v2-block{block['block']:02d}-r1"
        reportpath = path.parent / f"block{block['block']:02d}-r1-native/result.json"
        report = read(reportpath)
        report_sha = sha(reportpath)
        if (
            report["run_id"] != namespace
            or report["planned"] != 48
            or len(report["outcomes"]) != 48
        ):
            raise ValueError("native complete outcome denominator")
        outcomes = {v["family"]: v for v in report["outcomes"]}
        if len(outcomes) != 48 or any(
            v["status"] not in ("goal", "draw") for v in outcomes.values()
        ):
            raise ValueError("censor/UNKNOWN cannot become terminal z")
        distance = np.fromfile(path / "distance.f32", dtype="<f4").reshape(-1, 2)
        manifest = read(path / "cache.json")
        rows = []
        family_map = {}
        with (path / "rows.jsonl").open() as stream:
            for i, line in enumerate(stream):
                row = json.loads(line)
                p, q = public[row["id"]], private[row["id"]]
                family = p["canonical_family"]
                owner = assignment[family]
                outcome = outcomes[row["group"]]
                if outcome["status"] == "goal" and outcome["winner"] not in (0, 1):
                    raise ValueError("true GOAL must advertise P1/P2 winner")
                expected_z = (
                    0
                    if outcome["status"] == "draw"
                    else (1 if row["side"] - 1 == outcome["winner"] else -1)
                )
                if row["z"] != expected_z or row["split"] != "train":
                    raise ValueError("true native STM terminal outcome/partition differs")
                if outcome["status"] == "draw" and (
                    outcome["winner"] is not None or outcome["reason"] is not None
                ):
                    raise ValueError("draw needs original native terminal outcome, not cap/fault")
                if owner["native_family"] != row["group"] or owner["native_run_id"] != namespace:
                    raise ValueError("original canonical family alias")
                if (
                    outcome["moves"][: len(q["prefix"])] != q["prefix"]
                    or len(q["prefix"]) != row["ply"]
                ):
                    raise ValueError("row prefix does not match complete terminal game")
                if outcome["moves"][: len(owner["prefix"])] != owner["prefix"]:
                    raise ValueError("registered opening prefix differs")
                actual_ids = row["ids"] if row["side"] == 1 else row["ids"][::-1]
                bits = distance[i].view("<u4").tolist()
                if q["ids_order"] != "P1_then_P2" or q["side"] != row["side"]:
                    raise ValueError("private input view source metadata")
                private_ids = q["ids"] if q["side"] == 1 else q["ids"][::-1]
                if actual_ids != p["actualSTM_ids"] or actual_ids != private_ids:
                    raise ValueError("P1P2-to-STM input projection differs")
                if bits != p["STM_distance_f32bits"] or bits != q["distance_bits"]:
                    raise ValueError("actual rawdistance f32 bits differ")
                if row["state_key"] != p["state_key"] or row["history_key"] != q["history_key"]:
                    raise ValueError("state/history projection differs")
                literal = json.dumps(
                    q["history_literal"], separators=(",", ":"), ensure_ascii=False
                )
                literal_sha = hashlib.sha256(literal.encode()).hexdigest()
                if literal_sha != q["history_key"]:
                    raise ValueError("registered native serde history literal/hash format")
                ref = {
                    "id": namespace + ":" + row["id"],
                    "source_id": row["id"],
                    "canonical_family": family,
                    "partition": owner["new_split"],
                    "cohort": owner["cohort"],
                    "opening_side": owner["opening_side"],
                    "side": row["side"],
                    "ply": row["ply"],
                    "actualSTM_ids": actual_ids,
                    "STM_distance_f32bits": bits,
                    "input_signature": input_signature(actual_ids, bits),
                    "input_signature_format": "QF1-f32-STM-v1_NUL_u16lengthsIDs_f32bits",
                    "state_key": row["state_key"],
                    "history_literal_SHA": literal_sha,
                    "history_key": row["history_key"],
                    "history_format": q["history_format"],
                    "prefix_witness": {
                        "path": block["private_input_only_witness"],
                        "SHA": block["private_input_only_SHA"],
                        "id": row["id"],
                    },
                }
                raw_refs.append((ref, literal))
                rows.append((row, ref))
                family_map[row["group"]] = {
                    "canonical_family": family,
                    "partition": owner["new_split"],
                }
                outcomes_seen[family] = {
                    "canonical_family": family,
                    "status": outcome["status"],
                    "winner": outcome["winner"],
                    "final_prefix": outcome["moves"],
                    "native_report": str(reportpath),
                    "native_report_SHA": report_sha,
                }
                if len([v for v in witness if v["partition"] == owner["new_split"]]) < 6:
                    witness.append({**ref, "prefix": q["prefix"]})
        if len(rows) != manifest["rows"] or len(rows) != block["rows_before_OR"]:
            raise ValueError("all original raw rows denominator")
        shard_data.append(
            {
                "path": str(path),
                "manifest_SHA": block["cache_manifest_SHA"],
                "namespace": namespace,
                "family_map": family_map,
                "rows": rows,
            }
        )
        references.extend(
            [
                {"path": block["public_metadata"], "SHA": block["public_SHA"]},
                {
                    "path": block["private_input_only_witness"],
                    "SHA": block["private_input_only_SHA"],
                },
                {"path": str(reportpath), "SHA": report_sha},
            ]
        )
    if len(raw_refs) != 19536 or len(outcomes_seen) != 576:
        raise ValueError("576 complete families/19536 raw rows required")
    status = Counter(o["status"] for o in outcomes_seen.values())
    if status != {"goal": 575, "draw": 1}:
        raise ValueError("original575GOAL+1trueDRAW binding")
    val = [(r, literal) for r, literal in raw_refs if r["partition"] == "validation"]
    keys = {
        "state": {r["state_key"] for r, _ in val},
        "history_literal": {literal for _, literal in val},
        "actual_input": {r["input_signature"] for r, _ in val},
    }
    matches = Counter()
    train, allval = [], []
    for ref, literal in raw_refs:
        bits = {
            "state": ref["state_key"] in keys["state"],
            "history_literal": literal in keys["history_literal"],
            "actual_input": ref["input_signature"] in keys["actual_input"],
        }
        excluded = ref["partition"] == "train" and any(bits.values())
        if ref["partition"] == "train":
            for key, value in bits.items():
                matches[key] += value
            matches["OR"] += excluded
            if not excluded:
                train.append(ref)
        else:
            allval.append(ref)
        ref["primary_eligible"] = not excluded
    for part, refs in (("Tseen", train), ("Vraw", allval)):
        with gzip.open(SCOPE / (part + "-input-references.jsonl.gz"), "wt") as stream:
            for row in refs:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    for shard in shard_data:
        shard["rows"] = [
            {"index": i, "id": row["id"], "primary_eligible": ref["primary_eligible"]}
            for i, (row, ref) in enumerate(shard["rows"])
        ]
    references.append({"path": reg["split"], "SHA": sha(reg["split"])})
    parent = {
        "schema": "quoridor-sharded-training-cache-v1",
        "feature_count": 312,
        "rows": 19536,
        "shards": shard_data,
        "references": references,
    }
    write(SCOPE / "sharded-cache-v1.json", parent)
    eligible_families = Counter(r["canonical_family"] for r in train)
    planned = Counter(f["new_split"] for f in assignment.values())
    draw = next(v for v in outcomes_seen.values() if v["status"] == "draw")
    write(
        SCOPE / "native-witness-v1.json",
        {"rows": witness, "draw": draw, "NN": 0, "no_ruleA_replay_here": True},
    )
    write(
        SCOPE / "input-preparation-result-v1.json",
        {
            "task": reg["task"],
            "schema": "native-z-preparation-v1",
            "UTC": datetime.now(timezone.utc).isoformat(),
            "rawrows": 19536,
            "T": len(train),
            "Vraw": len(allval),
            "Tplannedfamilies": planned["train"],
            "Vplannedfamilies": planned["validation"],
            "Teligiblefamilies": len(eligible_families),
            "Tzeroeligible": planned["train"] - len(eligible_families),
            "OR": dict(matches),
            "outcomes": dict(status),
            "true_draw_binding": draw,
            "new_test_opened": False,
            "old_corpus_new_selection_is_not_blind": True,
            "history_crosspublic": "UNAVAILABLE",
            "NN": 0,
            "source_seconds": time.monotonic() - started,
            "loader": {
                "path": str(SCOPE / "sharded-cache-v1.json"),
                "SHA": sha(SCOPE / "sharded-cache-v1.json"),
            },
            "references": {
                n: {
                    "path": str(SCOPE / (n + "-input-references.jsonl.gz")),
                    "SHA": sha(SCOPE / (n + "-input-references.jsonl.gz")),
                }
                for n in ("Tseen", "Vraw")
            },
            "all_actualused_union_is_conservative_eligible_T": True,
        },
    )
    print(
        json.dumps(
            {
                "task": reg["task"],
                "T": len(train),
                "Vraw": len(allval),
                "OR": dict(matches),
                "NN": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
