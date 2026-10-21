"""Bounded scientific observations; lifecycle receipt parsing lives at one caller.

This function consumes already-bound views. It does not admit a build, certify a
run, launch a child, write outputs or publish authoritative completion.
"""

import producer355 as p
import strength355 as s


def aggregate_observations(index, inputs, partial, book, schedule, run_context):
    """Keep planned UNKNOWN slots and partial sections on the original error."""
    try:
        return _aggregate_observations(index, inputs, partial, book, schedule, run_context)
    except BaseException as primary:
        primary.strength355_available_evidence = partial
        primary.strength355_input_progress = inputs.progress
        raise


def _aggregate_observations(index, inputs, partial, book, schedule, run_context):
    s.require(len(index["batches"]) <= 16, "fixed batch denominator")
    by_batch = {}
    for batch in index["batches"]:
        number = s.integer(batch["batch"], 0, 15)
        s.require(number not in by_batch, "duplicate batch")
        by_batch[number] = batch

    def games():
        for number, batch in sorted(by_batch.items()):
            config = inputs.get(batch["config"])
            slots = {r["local_game"]: r for r in schedule["slots"] if r["batch_id"] == number}
            for raw in inputs.lines(batch["completed"]):
                local = s.integer(raw["game"], 0, 31)
                slot = slots[local]
                # Expected scientific context, not an observed historical start receipt.
                expected = {
                    "game": local,
                    "family": f"{config['run_id']}-family-{local // 2:06}",
                    "candidate_color": slot["candidate_colour"],
                    "opening": config["arena"]["book"]["openings"][local // 2]["prefix"],
                }
                yield s.adapt_native_game(raw, expected, config, slot, book, schedule)

    partial["games"] = s.aggregate_games(book, schedule, games(), inputs.progress)
    inputs.progress["available_sections"].append("games")
    rows = []
    partial["matched_available_rows"] = rows
    for name in index["matched_rows"]:
        rows.append(p.search_row(inputs.get(name), book))
    matched = s.check_matched(book, {"book_SHA256": s.check_book(book), "rows": rows})
    partial["matched"] = matched
    selection = None
    stronger_rows = []
    partial["stronger_available_rows"] = stronger_rows
    if index["selection"] is not None:
        raw_selection = inputs.get(index["selection"])
        content = p.frozen_selection(raw_selection, matched, book)
        source_sha = inputs.refs[index["selection"]]["SHA256"]
        # Verify selection references every available matched file. String/order
        # booleans alone do not authenticate publication or source control flow.
        actual_refs = raw_selection["matched_outputs"]
        expected_refs = [inputs.refs[name] for name in index["matched_rows"]]
        s.require(
            sorted((x["path"], x["sha256"], x["bytes"]) for x in actual_refs)
            == sorted((x["path"], x["SHA256"], x["bytes"]) for x in expected_refs),
            "durable pre-stronger matched references",
        )
        selection = {"content": content, "content_SHA256": s.digest(content)}
        for descriptor in index["stronger_rows"]:
            row = p.search_row(inputs.get(descriptor["file"]), book, descriptor["kind"])
            s.require(
                row["source_selection_SHA256"] == source_sha, "actual stronger physical selection"
            )
            row["selection_SHA256"] = selection["content_SHA256"]
            stronger_rows.append(row)
        # Ordinal proof, NOT invented runtime timestamps. Qualified exact source
        # syncs these durable references before it can invoke stronger calls.
        events = [
            {"kind": "MATCHED_STOP", "sequence": 0},
            {
                "kind": "SELECTION_FSYNC",
                "sequence": 1,
                "selection_SHA256": selection["content_SHA256"],
            },
        ]
        if stronger_rows:
            events.append({"kind": "STRONGER_FIRST_CALL", "sequence": 2})
        partial["stronger"] = s.check_stronger(
            matched, selection, {"stage_events": events, "rows": stronger_rows}
        )
        partial["stronger"]["ordering_proof"] = {
            "basis": "accepted lifecycle artifact/experiment plus exact durable references; not wall timestamps",
            "run_context": run_context,
            "physical_selection_SHA256": source_sha,
        }
    else:
        s.require(not index["stronger_rows"], "stronger has no frozen selection")
        partial["stronger"] = {"status": "UNKNOWN", "campaign_upper_calls": 192}
    trees, seen = [], set()
    partial["trees_available"] = trees
    for name in index["trees"]:
        raw = inputs.get(name, 16777216)
        tree = p.common_tree(raw, book)
        s.require(tree["family_id"] not in seen, "duplicate common tree")
        seen.add(tree["family_id"])
        checked = s.check_tree(tree)
        checked["available_nodes"] = tree["expanded_plus_leaf_nodes"]
        checked["actual_leaf_evaluator_calls"] = raw.get("actual_leaf_evaluator_calls")
        trees.append(checked)
    s.require(sum(t["available_nodes"] for t in trees) <= 800000, "shared tree envelope")
    partial["trees"] = trees
    partial["unentered_tree_family_ids"] = sorted(set(s.TREE_IDS) - seen)
    partial.update(
        schema="quoridor.strength355.joint-summary.v1",
        provenance=book["provenance"],
        plan_SHA256=s.PLAN_SHA,
        producer_bindings=index["producer_bindings"],
        partial_errors=index["partial_errors"],
        scope="conditional common-root family inference; depth estimates not terminal truth/labels; no population/default/unique universal cause",
    )
    inputs.after()
    return partial
