"""Bind complete RuleA trajectories to sealed z and a target-free input projection."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import time


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def compressed_copy(source, target):
    with Path(source).open("rb") as src, gzip.open(target, "xb") as dst:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            dst.write(chunk)
    expected = sha(source)
    restored = hashlib.sha256()
    with gzip.open(target, "rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            restored.update(chunk)
    assert restored.hexdigest() == expected
    Path(source).unlink()  # Only this owner's temporary projection, after full restoration proof.
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    cfg = read(parser.parse_args().config)
    began = time.monotonic()
    for path, expected in cfg["source_hashes"].items():
        assert sha(path) == expected, "SOURCE_SHA:" + path
    assert not Path(cfg["output"]).exists()
    families = read(cfg["family_map"])["families"]
    aliases = {p["native_family"]: p for p in families}
    result = read(Path(cfg["native_root"]) / "result.json")
    assert result["run_id"] == families[0]["native_run_id"] and result["planned"] == 48
    outcomes = {r["family"]: r for r in result["outcomes"]}
    assert set(outcomes) == set(aliases)
    dataset = Path(cfg["dataset"])
    manifest = read(dataset / "manifest.json")
    for shard in manifest["shards"]:
        assert Path(shard["path"]).name == shard["path"]
        assert sha(dataset / shard["path"]) == shard["sha256"]
    private = Path(cfg["private_projection_temp"])
    subprocess.run([cfg["input_reader"], str(dataset), str(private)], check=True)
    scalar = Path(cfg["sealed_scalar_temp"])
    subprocess.run(
        [
            cfg["scalar_reader"],
            "labels",
            "--input",
            str(dataset),
            "--output",
            str(scalar),
            "--allow-test",
        ],
        check=True,
    )
    scalar_rows = {}
    with scalar.open() as source:
        for line in source:
            row = json.loads(line)
            key = (row["native_family"], row["id"])
            assert key not in scalar_rows
            scalar_rows[key] = row
    public = Path(cfg["public_projection_temp"])
    counts = Counter()
    eligible = Counter()
    with private.open() as source, public.open("x") as destination:
        for line in source:
            row = json.loads(line)
            p = aliases[row["native_family"]]
            game = outcomes[row["native_family"]]
            assert row["partition"] == "test"
            assert row["prefix"][: p["cohort"]] == p["prefix"]
            assert row["prefix"] == game["moves"][: row["ply"]]
            assert row["side"] == 1 + row["ply"] % 2
            label = scalar_rows.pop((row["native_family"], row["id"]))
            z = label["z"]
            if game["status"] == "unknown":
                assert z is None
            elif game["status"] == "draw":
                assert z == 0.0 and game["winner"] is None
                eligible[p["canonical_family"]] += 1
            else:
                assert game["status"] == "goal" and game["winner"] in (0, 1)
                assert z == (1.0 if game["winner"] + 1 == row["side"] else -1.0)
                eligible[p["canonical_family"]] += 1
            views = [row["side"] - 1, 2 - row["side"]]
            ids = [row["ids"][v] for v in views]
            assert all(sorted(set(v)) == v and all(0 <= i < 312 for i in v) for v in ids)
            clean = {
                "id": row["id"],
                "canonical_family": p["canonical_family"],
                "native_family_alias": row["native_family"],
                "partition": "sealed_rulea_transfer_observation",
                "side": row["side"],
                "ply": row["ply"],
                "cohort": p["cohort"],
                "opening_side": p["opening_side"],
                "state_key": row["state_key"],
                "history_key": row["history_key"],
                "history_literal": row["history_literal"],
                "history_key_format": row["history_format"],
                "actualSTM_ids": ids,
                "ids_order": "STM_then_opponent",
                "STM_distance_f32bits": row["distance_bits"],
                "distance_order": "STM_then_opponent_f32_le",
                "input_signature": row["input_signature"],
                "prefix": row["prefix"],
                "producer_schema": row["producer_schema"],
                "producer_source_SHA": cfg["producer_source_SHA"],
            }
            assert len(row["distance_bits"]) == 2
            distances = [struct.unpack("<f", struct.pack("<I", b))[0] for b in row["distance_bits"]]
            assert all(math.isfinite(d) and d >= 0 for d in distances)
            destination.write(json.dumps(clean, separators=(",", ":"), allow_nan=False) + "\n")
            counts[p["canonical_family"]] += 1
    assert not scalar_rows and sum(counts.values()) == sum(s["rows"] for s in manifest["shards"])
    proofs = {}
    for src, dst in (
        (private, cfg["private_projection_gz"]),
        (public, cfg["public_projection_gz"]),
        (scalar, cfg["sealed_scalar_gz"]),
    ):
        proofs[str(dst)] = {"SHA": sha(dst) if Path(dst).exists() else None}
        proofs[str(dst)]["uncompressed_SHA"] = compressed_copy(src, dst)
        proofs[str(dst)]["SHA"] = sha(dst)
    public_handoff = {
        "task": "rulea-z-transfer-292-v1",
        "schema": "rulea-z-transfer-targetfree-handoff-v1",
        "planned_family_count": 48,
        "row_count": sum(counts.values()),
        "rows_by_family": {p["canonical_family"]: counts[p["canonical_family"]] for p in families},
        "target_free_refs": cfg["public_projection_gz"],
        "projection_proof": proofs[cfg["public_projection_gz"]],
        "family_map_SHA": sha(cfg["family_map"]),
        "producer_labels_sealed": True,
        "history_cross_public": "public history unavailable; literal equality alone is not nonexposure proof",
        "mask": "NOT_FROZEN; independent291 allpublicTseen plus ALLrawV input exposure references required",
        "independent_prediction": "NOT_RUN",
    }
    with Path(cfg["public_handoff"]).open("x") as output:
        output.write(json.dumps(public_handoff, indent=2) + "\n")
    report = {
        "task": "rulea-z-transfer-292-export-v1",
        "schema": "rulea-z-transfer-export-v1",
        "NN": 0,
        "raw_manifest_SHA": sha(dataset / "manifest.json"),
        "all48_status": Counter(r["status"] for r in outcomes.values()),
        "all48_rows": public_handoff["rows_by_family"],
        "all48_eligible_z_rows": {
            p["canonical_family"]: eligible[p["canonical_family"]] for p in families
        },
        "sealed_labels": cfg["sealed_scalar_gz"],
        "compression_restore_proofs": proofs,
        "source_hashes": cfg["source_hashes"],
        "public_handoff_SHA": sha(cfg["public_handoff"]),
        "whole_command_wall_s": time.monotonic() - began,
        "cache_duplication": False,
        "separate_rootmean_optional": True,
    }
    with Path(cfg["output"]).open("x") as output:
        output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
