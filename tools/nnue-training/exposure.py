"""Label-free exposure detection for explicit partitions.

The caller supplies the complete comparison universe before selection. No
fixed game count or scientific split policy is implied by this shared code.
"""

from qf1 import feature_signature


def signatures(row):
    if not row.get("state_key") or not row.get("history_key"):
        raise ValueError("missing label-free state/history signature")
    return [
        ("state", row["state_key"]),
        ("history", row["history_key"]),
        ("QF1", feature_signature(row)),
    ]


def make_exposure_mask(rows, *, rule="state OR history OR STM-QF1 input sharing"):
    ids, family_splits, game_splits = set(), {}, {}
    for row in rows:
        if any(key in row for key in ("rootmean", "z", "z_stm", "loss", "rootNN", "winner")):
            raise ValueError("labels prohibited in exposure-mask input")
        if row["id"] in ids or row["split"] not in ("train", "validation", "test"):
            raise ValueError("duplicate ID or invalid partition")
        ids.add(row["id"])
        for seen, key in [
            (family_splits, row["group"]),
            (game_splits, row.get("game_id", row["group"])),
        ]:
            if key in seen and seen[key] != row["split"]:
                raise ValueError("game/family crosses partition")
            seen[key] = row["split"]
    training = {
        signature for row in rows if row["split"] == "train" for signature in signatures(row)
    }
    training_and_validation = training | {
        signature for row in rows if row["split"] == "validation" for signature in signatures(row)
    }
    masks, groups = {}, {}
    for row in rows:
        reference = training if row["split"] == "validation" else training_and_validation
        shared = (
            []
            if row["split"] == "train"
            else [signature[0] for signature in signatures(row) if signature in reference]
        )
        masks[row["id"]] = {
            "primary_eligible": not shared,
            "exposure": sorted(set(shared)),
            "split": row["split"],
            "group": row["group"],
        }
        group = groups.setdefault(
            row["group"],
            {
                "split": row["split"],
                "rows": 0,
                "eligible": 0,
            },
        )
        group["rows"] += 1
        group["eligible"] += not shared
    return {
        "rule": rule,
        "rows": masks,
        "games": groups,
        "feature_version": "QF1",
        "labels_used": False,
        "zero_eligible_games": sorted(
            group for group, value in groups.items() if not value["eligible"]
        ),
    }
